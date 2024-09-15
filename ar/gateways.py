# This file is part of PyArweave.
# 
# PyArweave is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 2 of the License, or (at your option) any later
# version.
# 
# PyArweave is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# PyArweave. If not, see <https://www.gnu.org/licenses/>.

import bisect, random, sys, time
from math import inf
import hashlib, json, requests
import tqdm

REF = {
    'algorithm': hashlib.sha512,
    'requests': [{
        'name': '100k ditem',
        'path': 'hOll2P-jMFJ4GX-7bp51ZBypeJoTyEXFxSJLquaCR_s', 
        'payload': None,
        'headers': {},#dict(Range='bytes=-65536'),
        'size': 101323,
        'hexdigest': 'a78261e6c930d335602b77ca02ff032e9fbfc1a5efeb3feb80707716c088f639783a7d0d691de68325e8d60918d66cc78f12dec9d53170f499dd6a5d77f4cd61',
    }, {
        'name': 'unconfirmed graphql tx',
        'path': 'graphql',
        'headers': {'Content-Type': 'application/json'},
        'payload': json.dumps({'operationName':None,'query':'query{transactions(sort:HEIGHT_DESC,first:1){edges{node{block{id height}}}}}','variables':{}}),
        'size': len('{"data":{"transactions":{"edges":[{"node":{"block":null}}]}}}\n'),
        'hexdigest': hashlib.sha512('{"data":{"transactions":{"edges":[{"node":{"block":null}}]}}}\n'.encode()).hexdigest(),
    }]
}

def fetch_from_registry(cu = None, process_id = None, raw = False):
    import ao, json
    cu = cu or ao.cu(host='https://cu.ar-io.dev')
    process_id = process_id or ao.AR_IO_TESTNET_PROCESS_ID
    tags = {
        'Action': 'Paginated-Gateways',
        'Data-Protocol': 'ao',
        'Type': 'Message',
        'Variant': 'ao.TN.1',
        # Sort-Order, Limit, Sort-By
    }
    kwparams = {
        'process_id': process_id,
        'id': '1234',
        'target': process_id,
        'owner': '1234',
        'anchor': '0',
        'data': '12345',
        'tags': tags,
    }
    result = dict(hasMore=True)
    while True:
        result = json.loads(cu.dry_run(**kwparams)['Messages'][0]['Data'])
        if raw:
            yield from result['items']
        else:
            for gw in result['items']:
                if gw['status'] == 'joined':
                    settings = gw['settings']
                    protoport = [settings['protocol'], settings['port']]
                    if protoport in [['http',80],['https',443]]:
                        yield '{protocol}://{fqdn}'.format(**settings)
                    else:
                        yield '{protocol}://{fqdn}:{port}'.format(**settings)
        if not result['hasMore']:
            break
        tags['Cursor'] = result['nextCursor']

def _make_gw_stat(url):
    start = time.time()
    for request in REF['requests']:
        content = b''
        if request['payload'] is None:
            response = requests.get(url + '/' + request['path'], headers=request.get('headers'), timeout=15, stream=True)
        else:
            response = requests.post(url + '/' + request['path'], data = request['payload'], headers=request.get('headers'), timeout=15, stream=True)
        with response as network_stream:
            content = network_stream.raw.read(request['size'])
        duration = time.time() - start
        if len(content) < request['size']:
            raise ValueError('Short content')
        if REF['algorithm'](content).hexdigest() != request['hexdigest']:
            raise ValueError('Incorrect content')
    return duration

def _add(gw):
    try:
        time = _make_gw_stat(gw)
    except (ValueError, OSError) as exc:
        BAD.append(gw)
        return len(GOOD) + len(BAD) - 1
    else:
        idx = bisect.bisect(TIMES, time)
        TIMES.insert(idx, time)
        GOOD.insert(idx, gw)
        return idx

def _pop(idx_or_url):
    if type(idx_or_url) is int:
        if idx_or_url >= len(GOOD):
            url = BAD.pop(idx_or_url-len(GOOD))
        else:
            url = GOOD.pop(idx_or_url)
            TIMES.pop(idx_or_url)
        return url
    else:
        try:
            idx = GOOD.index(idx_or_url)
            GOOD.pop(idx)
            TIMES.pop(idx)
        except ValueError:
            idx = BAD.index(idx_or_url)
            BAD.pop(idx)
        return idx

def fetch_and_update_new(cu = None, process_id = None):
    new_gws = []
    stale_gws = set()
    possible_stale_gws = []
    for gw in fetch_from_registry(cu = cu, process_id = process_id):
        if gw not in GOOD and gw not in BAD:
            new_gws.append(gw)
            stale_gws.update(possible_stale_gws)
            possible_stale_gws = []
        else:
            possible_stale_gws.append(gw)
            if len(possible_stale_gws) > 49:
                break
    if new_gws:
        print('Measuring', len(new_gws) + len(stale_gws), 'new or updated gateways.', file=sys.stderr)
        with tqdm.tqdm(new_gws[::-1], unit='gw') as pbar:
            for gw in pbar:
                pbar.set_description(gw, False)
                _add(gw)
                write()
        with tqdm.tqdm(stale_gws, unit='gw') as pbar:
            for gw in pbar:
                pbar.set_description(gw, False)
                _pop(gw)
                _add(gw)
                write()

def update_best(count = 2):
    with tqdm.tqdm(range(count), unit='best gw') as pbar:
        for best in pbar:
            url = _pop(best)
            rank = _add(url)
            while rank > best:
                if rank >= len(GOOD):
                    pbar.set_description('no longer good: ' + url, refresh=True)
                else:
                    pbar.set_description('no longer best: ' + url, refresh=True)
                url = _pop(best)
                rank = _add(url)
            pbar.set_description('best: ' + url)
        pbar.set_description('writing')
        write()

def update_one():
    idx = int(random.random() * random.random() * (len(GOOD)+len(BAD)))
    _add(_pop(idx))
    write()

def update_all():
    time_urls = []
    bad = []
    with tqdm.tqdm(BAD + GOOD, unit='gw') as pbar:
        for url in pbar:
            try:
                time_urls.append([_make_gw_stat(url),url])
                pbar.set_description(url)
            except (ValueError, OSError):
                bad.append(url)
                pbar.set_description('bad: ' + url, refresh=False)
        pbar.set_description('sorting ' + str(len(GOOD)) + ' gws')
        time_urls.sort()
        TIMES[:] = [time_url[0] for time_url in time_urls]
        GOOD[:] = [time_url[1] for time_url in time_urls]
        BAD[:] = bad
        pbar.set_description('writing ' + str(len(GOOD)) + ' gws')
        write()
        pbar.set_description(str(len(GOOD)) + ' accessible gateways')

def write():
    with open(__file__,'r+t') as fh:
        content = fh.read()
        start = content.rfind('TIMES = ')
        end = content.find('\n', content.find('BAD = ', start))
        fh.seek(start)
        fh.write('TIMES = ' + repr(TIMES) + '\n\nGOOD = ' + repr(GOOD) + '\n\nBAD = ' + repr(BAD) + content[end:])
        fh.truncate()

TIMES = [0.4068613052368164, 0.5134055614471436, 0.6121687889099121, 0.6189093589782715, 0.6493649482727051, 0.7018187046051025, 0.7309796810150146, 0.7497751712799072, 0.815605640411377, 0.8349707126617432, 0.8457844257354736, 0.849327564239502, 0.9091048240661621, 1.0558595657348633, 1.1368951797485352, 1.1673827171325684, 1.2059075832366943, 1.2290892601013184, 1.7267916202545166, 1.8327438831329346, 2.0105197429656982, 2.046461820602417, 2.061734914779663, 2.1157498359680176, 2.1364405155181885, 2.145052909851074, 2.1461379528045654, 2.1501364707946777, 2.1660356521606445, 2.189028739929199, 2.19250226020813, 2.196291446685791, 2.2133686542510986, 2.2436985969543457, 2.2445082664489746, 2.2453629970550537, 2.2513320446014404, 2.252124309539795, 2.2535648345947266, 2.2538418769836426, 2.2551329135894775, 2.2675728797912598, 2.2729780673980713, 2.275744676589966, 2.2820327281951904, 2.285299301147461, 2.2975339889526367, 2.3034138679504395, 2.3053128719329834, 2.309379816055298, 2.3205108642578125, 2.331556558609009, 2.3353018760681152, 2.340757131576538, 2.353837013244629, 2.3556337356567383, 2.358835458755493, 2.3651232719421387, 2.36822772026062, 2.3707199096679688, 2.37333345413208, 2.3750059604644775, 2.379673957824707, 2.3798635005950928, 2.385260820388794, 2.3898732662200928, 2.393472194671631, 2.394759178161621, 2.403325080871582, 2.4073567390441895, 2.4077577590942383, 2.408769369125366, 2.424600601196289, 2.4373250007629395, 2.4573628902435303, 2.4585883617401123, 2.4587342739105225, 2.461578845977783, 2.463233709335327, 2.476478099822998, 2.477510929107666, 2.4855306148529053, 2.4864718914031982, 2.4898622035980225, 2.4986917972564697, 2.511575698852539, 2.525026559829712, 2.525092840194702, 2.526902437210083, 2.5335705280303955, 2.547731399536133, 2.5494306087493896, 2.5498692989349365, 2.559514045715332, 2.559641122817993, 2.5599820613861084, 2.5601091384887695, 2.56131911277771, 2.567538022994995, 2.574659824371338, 2.585019111633301, 2.595691680908203, 2.5965800285339355, 2.5973246097564697, 2.60723614692688, 2.6112074851989746, 2.6186070442199707, 2.6267242431640625, 2.6299619674682617, 2.634307861328125, 2.6370575428009033, 2.6599037647247314, 2.661262035369873, 2.661369800567627, 2.6613833904266357, 2.6620051860809326, 2.6630749702453613, 2.6634089946746826, 2.6639816761016846, 2.664302349090576, 2.6692073345184326, 2.727672815322876, 2.7317557334899902, 2.7460951805114746, 2.7536847591400146, 2.7561614513397217, 2.7605888843536377, 2.7632129192352295, 2.763484477996826, 2.763735294342041, 2.7643864154815674, 2.7644057273864746, 2.764586925506592, 2.765129566192627, 2.7655715942382812, 2.766373634338379, 2.766719341278076, 2.7741191387176514, 2.7785494327545166, 2.807027578353882, 2.8231778144836426, 2.835958957672119, 2.85854172706604, 2.8665342330932617, 2.8674278259277344, 2.8694827556610107, 2.9083707332611084, 2.921421527862549, 2.924288272857666, 2.9519169330596924, 2.966587781906128, 2.9680182933807373, 2.9680495262145996, 2.968883991241455, 3.0720486640930176, 3.0847713947296143, 3.13411808013916, 3.181546449661255, 3.2419779300689697, 3.3078577518463135, 3.32643723487854, 3.3394155502319336, 3.359657049179077, 3.3799214363098145, 3.436973810195923, 3.450538396835327, 3.480367422103882, 3.5095794200897217, 3.535886287689209, 3.6434972286224365, 3.654658555984497, 3.6757888793945312, 4.096247673034668, 4.198251724243164, 4.3011314868927, 4.340612888336182, 4.375317335128784, 4.402107238769531, 4.403928995132446, 4.464782476425171, 4.606748819351196, 4.652719497680664, 4.710646629333496, 7.194764137268066, 13.023943662643433, 17.613125801086426, 17.614022493362427, 18.942639589309692]

GOOD = ['https://arweave.developerdao.com', 'https://arweave.net', 'https://aothecomputer.xyz', 'https://adaconna.top', 'https://ario-testnet.us.nodefleet.org', 'https://exodusdiablo.xyz', 'https://dwentz.site', 'https://iogate.uk', 'https://stonkson.xyz', 'https://iogate.co.uk', 'https://aksamlan.xyz', 'https://vrising.site', 'https://ozzcanx.xyz', 'https://flashwayne.online', 'https://frostor.xyz', 'https://utkububa.xyz', 'https://aoweave.tech', 'https://apeweave.com', 'https://nodebiz.site', 'https://arioarioario.online', 'https://ahmkahvalidator.xyz', 'https://nodehub.site', 'https://ar.ilaybilge.xyz', 'https://thd.io.vn', 'https://redwhiteconnect.xyz', 'https://software0x.space', 'https://snafyr.xyz', 'https://anti-mage01.store', 'https://mssnodes.xyz', 'https://ioar.xyz', 'https://flechemano.com', 'https://spectre01.site', 'https://alexxis.store', 'https://oshvank.site', 'https://maclaurino.xyz', 'https://bicem.xyz', 'https://torku.xyz', 'https://ar.kiranli.xyz', 'https://vnnode.top', 'https://sarlos.site', 'https://frogzz.xyz', 'https://sakultarollapp.site', 'https://nodezeta.site', 'https://bootstrap.icu', 'https://slatrokh.xyz', 'https://blessingway.xyz', 'https://alicans.online', 'https://practicers.xyz', 'https://senzura.xyz', 'https://campnode.xyz', 'https://elessardarken.xyz', 'https://treexyz.site', 'https://doflamingo.xyz', 'https://mrciga.com', 'https://recepgocmen.xyz', 'https://nodetitan.site', 'https://sametyuksel.xyz', 'https://hexamz.tech', 'https://coshift.xyz', 'https://mrheracles.online', 'https://vikanren.buzz', 'https://liglow.com', 'https://vevivofficial.xyz', 'https://ariogateway.online', 'https://arnode.site', 'https://weaversnodes.info', 'https://chaintech.site', 'https://zerolight.online', 'https://adn79.pro', 'https://nodetester.com', 'https://regaret.xyz', 'https://kazazel.xyz', 'https://0xkullanici.online', 'https://erenynk.xyz', 'https://nodepepe.site', 'https://ar.tomris.xyz', 'https://ar.phuongvusolution.com', 'https://mulosbron.xyz', 'https://gatewaykeeper.net', 'https://zekkava.space', 'https://kunacan.xyz', 'https://grenimo.click', 'https://nodechecker.xyz', 'https://yakupgs.online', 'https://ar-arweave.xyz', 'https://nodevip.site', 'https://maplesyrup-ario.my.id', 'https://love4src.com', 'https://eaddaa.website', 'https://sowyer.xyz', 'https://ivandivandelen.online', 'https://stajertestnetci.site', 'https://pentav.site', 'https://ahnetd.online', 'https://zionalc.online', 'https://cyanalp.cfd', 'https://stilucky.top', 'https://ykpbb.xyz', 'https://mdbmesutmdb.shop', 'https://erenkurt.site', 'https://murod.xyz', 'https://aralper.xyz', 'https://kingsharaldoperator.xyz', 'https://merttemizer.xyz', 'https://tekin86.online', 'https://ademtor.xyz', 'https://kyotoorbust.site', 'https://cmdexe.xyz', 'https://sooneraydin.xyz', 'https://hazmaniaxbt.online', 'https://pi314.xyz', 'https://dtractusrpca.xyz', 'https://crbaa.xyz', 'https://hlldrk.shop', 'https://rikimaru111.site', 'https://canduesed.me', 'https://yolgezer55.xyz', 'https://tefera.xyz', 'https://euraquilo.xyz', 'https://krayir.xyz', 'https://mustafakaya.xyz', 'https://beyzako.xyz', 'https://htonka.xyz', 'https://arceina.store', 'https://baristestnet.xyz', 'https://darksunrayz.store', 'https://babayagax.online', 'https://rodruquez.online', 'https://khacasablanca.top', 'https://itsyalcin.xyz', 'https://alpt.autos', 'https://ruangnode.xyz', 'https://khaldrogo.site', 'https://karakartal.store', 'https://svgtmrgl.xyz', 'https://kabaoglu.xyz', 'https://boramir.store', 'https://iblis.store', 'https://sunkripto.site', 'https://mehteroglu.store', 'https://barburan.site', 'https://auquis.online', 'https://chocon.store', 'https://salakk.online', 'https://mustafakara.space', 'https://linaril.xyz', 'https://leechshop.com', 'https://kagithavlu.store', 'https://rtmpsunucu.online', 'https://ar.anyone.tech', 'https://ar.taskopru.xyz', 'https://terminatormbd.com', 'https://koltigin.xyz', 'https://0xyvz.xyz', 'https://kahvenodes.online', 'https://yukovskibot.com', 'https://0xsav.xyz', 'https://ar.riceinbucket.com', 'https://yusufaytn.xyz', 'https://araoai.com', 'https://2save.xyz', 'https://rollape.com.tr', 'https://vilenarios.com', 'https://koniq.xyz', 'https://ainodes.xyz', 'https://arweave.auduge.com', 'https://ar.0xskyeagle.com', 'https://ar.ionode.online', 'https://wenairdropsir.store', 'https://ar.bearnode.xyz', 'https://sulapan.com', 'https://fisneci.com', 'https://ar-node.megastake.org', 'https://arns-gateway.com', 'https://astrocosmos.website', 'https://ar.secret-network.xyz', 'https://adora0x0.xyz', 'https://ar-testnet.p10node.com', 'https://khang.pro', 'https://ar.satoshispalace.casino', 'https://ar.owlstake.com', 'https://imtran.site', 'https://katsumii.xyz', 'https://nodebeta.site', 'https://ario.dasamuka.xyz', 'https://kt10vip.online', 'https://thanhapple.store', 'https://meocon.store']

BAD = ['https://commissar.xyz', 'https://gisela-arg.xyz', 'https://sadas655.xyz', 'https://kenyaligeralt.xyz', 'https://ruyisu.net', 'https://0xmonyaaa.xyz', 'https://zirhelp.lol', 'https://gmajorscale.xyz', 'https://g8way.0rbit.co', 'https://misatoshi.pics', 'https://clyapp.xyz', 'https://dilsinay.online', 'https://secondtornado.xyz', 'https://mpsnode.online', 'https://gateway.getweave.org', 'https://comrat32.xyz', 'https://konobbeybackend.online', 'https://nodecoyote.xyz', 'https://sabrig1480.xyz', 'https://kingsharald.xyz', 'https://blockchainzk.website', 'https://vevivo.xyz', 'https://software0x.website', 'https://dasamuka.cloud', 'https://shapezero.xyz', 'https://bootstrap.lol', 'https://canduesed.xyz', 'https://nodeinvite.xyz', 'https://lethuan.xyz', 'https://bburan.xyz', 'https://velaryon.xyz', 'https://anch0r.com', 'https://thecoldblooded.online', 'https://moruehoca.online', 'https://cahil.store', 'https://dnsarz.wtf', 'https://rerererararags.store', 'https://validatorario.xyz', 'https://sefaaa.online', 'https://ahmkah.online', 'https://thecoldblooded.store', 'https://diafora.tech', 'https://berso.store', 'https://moruehoca.store', 'https://dilsinay2814.online', 'https://mutu.lol', 'https://cetinsefa.online', 'https://validatario.xyz', 'https://aantop.xyz', 'https://enesss.online', 'https://graski.xyz', 'https://wanr.top', 'https://arnode.cfd', 'https://aslanas01.xyz', 'https://jembutkucing.online', 'https://shadow39.online', 'https://jaxtothehell.xyz', 'https://parkdongfeng.store', 'https://r4dn.tech', 'https://darthlyrex.xyz', 'https://acanpolat.xyz', 'https://arnode.xyz', 'https://ar.qavurdagli.online', 'https://prowsemre.online', 'https://nodevietnam.com', 'https://sygnblock.xyz', 'https://bodhiirozt.xyz', 'https://coinhunterstr.site', 'https://techvenience.net', 'https://apayro.xyz', 'https://anaraydinli.xyz', 'https://mrcetin03.store', 'https://arweave.ar', 'https://cakonline.xyz', 'https://budavlebac.online', 'https://loriscant.site', 'https://0xsaitomo.xyz', 'https://neuweltgeld.xyz', 'https://arlogmein.xyz', 'https://arendor.xyz', 'https://ariozerowave.my.id', 'https://webraizo.online', 'https://xiaocloud.site', 'https://thekayz.xyz', 'https://captsuck.xyz', 'https://minhbear.xyz', 'https://Phuc.top', 'https://ibrahimdirik.xyz', 'https://sedat07.xyz', 'https://herculesnode.shop', 'https://cayu7pa.xyz', 'https://mahcubyan.xyz', 'https://0xknowledge.store', 'https://testnetnodes.xyz', 'https://gurkanceltin.online', 'https://stevnode.site', 'https://ongtrong.xyz', 'https://kecil.tech', 'https://myphamalma.com', 'https://lanchiaw.xyz', 'https://getblock.store', 'https://emireray.shop', 'https://lobosqlinc.site', 'https://polkasub.site', 'https://shapezero.site', 'https://ario.stake.nexus', 'https://digitclone.online', 'https://lostgame.online', 'https://mutu.pro', 'https://ar-dreamnode.xyz', 'https://diafora.site', 'https://aleko0o.store', 'https://vn-sti.top', 'https://flexibleee.xyz', 'https://soulbreaker.xyz', 'https://parafmax.site', 'https://omersukrubektas.online', 'https://node69.site', 'https://mertorakk.xyz', 'https://kanan1.shop', 'https://bsckapp.store', 'https://arweave.validator.wiki', 'https://arbr.pro', 'https://ar-io.dev', 'https://permagate.io', 'https://ariospeedwagon.com', 'https://g8way.io', 'https://ar.perplex.finance', 'https://kiem-tran.tech', 'https://dnsarz.site', 'https://arweaveblock.com', 'https://arweave.fllstck.dev', 'https://didzcover.world', 'https://bambik.online', 'https://deknow.top', 'https://ar.alwaysbedream.dev', 'https://lobibo.online', 'https://teoteovivi.store']
