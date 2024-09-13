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
import hashlib, requests
import tqdm

REF = [
    'hOll2P-jMFJ4GX-7bp51ZBypeJoTyEXFxSJLquaCR_s',
    {},#dict(Range='bytes=-65536'),
    101323,
    hashlib.sha512,
    'a78261e6c930d335602b77ca02ff032e9fbfc1a5efeb3feb80707716c088f639783a7d0d691de68325e8d60918d66cc78f12dec9d53170f499dd6a5d77f4cd61'
]

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
    content = b''
    with requests.get(url + '/' + REF[0], headers=REF[1], timeout=15, stream=True) as network_stream:
        content = network_stream.raw.read(REF[2])
    duration = time.time() - start
    if len(content) < REF[2]:
        raise ValueError('Short content')
    if REF[3](content).hexdigest() != REF[4]:
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

TIMES = [0.12508511543273926, 0.15632367134094238, 0.24101710319519043, 0.2574613094329834, 0.3047959804534912, 0.31964802742004395, 0.41950368881225586, 0.45002126693725586, 0.4639451503753662, 0.47214245796203613, 0.4889717102050781, 0.5106875896453857, 0.5233147144317627, 0.5342326164245605, 0.5392229557037354, 0.5702440738677979, 0.5764720439910889, 0.5820572376251221, 0.609285831451416, 0.6627485752105713, 0.6673831939697266, 0.9796626567840576, 1.026149034500122, 1.0314013957977295, 1.1113221645355225, 1.1123876571655273, 1.1181671619415283, 1.1302299499511719, 1.137592077255249, 1.1399223804473877, 1.140749454498291, 1.1427977085113525, 1.1436622142791748, 1.145028829574585, 1.146207332611084, 1.1640336513519287, 1.1673247814178467, 1.1690902709960938, 1.1702549457550049, 1.1706697940826416, 1.1723463535308838, 1.1760311126708984, 1.1761364936828613, 1.176222324371338, 1.1783180236816406, 1.180330753326416, 1.1836419105529785, 1.1878046989440918, 1.1899909973144531, 1.1901829242706299, 1.1928839683532715, 1.1941025257110596, 1.2025370597839355, 1.203110933303833, 1.2087082862854004, 1.213238000869751, 1.2143962383270264, 1.219425916671753, 1.2197964191436768, 1.2272100448608398, 1.2276926040649414, 1.2316925525665283, 1.2327561378479004, 1.233290195465088, 1.2392842769622803, 1.2439239025115967, 1.2517030239105225, 1.2535595893859863, 1.2668631076812744, 1.2725231647491455, 1.2750790119171143, 1.2765061855316162, 1.2785046100616455, 1.280409574508667, 1.2812469005584717, 1.2813467979431152, 1.2834994792938232, 1.2836363315582275, 1.284696340560913, 1.2867801189422607, 1.2872040271759033, 1.2956411838531494, 1.2972142696380615, 1.298922061920166, 1.2992699146270752, 1.3047270774841309, 1.307629108428955, 1.3099830150604248, 1.310279369354248, 1.310791254043579, 1.311009407043457, 1.3176307678222656, 1.3177733421325684, 1.3215148448944092, 1.3249197006225586, 1.3292438983917236, 1.3296775817871094, 1.333730936050415, 1.3364572525024414, 1.3369741439819336, 1.3370733261108398, 1.338559865951538, 1.3386578559875488, 1.3440394401550293, 1.3453357219696045, 1.348719596862793, 1.3513069152832031, 1.3526151180267334, 1.3546786308288574, 1.355020523071289, 1.3552594184875488, 1.3558847904205322, 1.356691837310791, 1.3568310737609863, 1.3570172786712646, 1.3578157424926758, 1.3579821586608887, 1.3605844974517822, 1.3635079860687256, 1.3649463653564453, 1.3671929836273193, 1.3684184551239014, 1.3698995113372803, 1.371626853942871, 1.3747620582580566, 1.3774280548095703, 1.377800703048706, 1.378178358078003, 1.3829257488250732, 1.3842618465423584, 1.3880081176757812, 1.389575719833374, 1.389765977859497, 1.3919200897216797, 1.3926503658294678, 1.3936100006103516, 1.394623041152954, 1.3946654796600342, 1.3951802253723145, 1.3972430229187012, 1.3999764919281006, 1.402937889099121, 1.4029455184936523, 1.407766342163086, 1.4082837104797363, 1.4100377559661865, 1.4103233814239502, 1.4133095741271973, 1.4155902862548828, 1.4219162464141846, 1.4248597621917725, 1.431835651397705, 1.4334454536437988, 1.434722661972046, 1.4491093158721924, 1.4530973434448242, 1.456188678741455, 1.4584851264953613, 1.4632785320281982, 1.4699699878692627, 1.4711191654205322, 1.4740865230560303, 1.4791460037231445, 1.4827077388763428, 1.4897332191467285, 1.4943163394927979, 1.5023770332336426, 1.5073919296264648, 1.5149052143096924, 1.521324872970581, 1.522273302078247, 1.523745059967041, 1.542288064956665, 1.5431876182556152, 1.5481340885162354, 1.554889440536499, 1.5954334735870361, 1.5963318347930908, 1.6027872562408447, 1.6069366931915283, 1.6242127418518066, 1.6318981647491455, 1.639101266860962, 1.6520628929138184, 1.661454677581787, 1.668637990951538, 1.6836864948272705, 1.6980242729187012, 1.7120299339294434, 1.7122161388397217, 1.7198822498321533, 1.7565138339996338, 1.7760193347930908, 1.7909493446350098, 1.9558601379394531, 1.9562089443206787, 2.016237497329712, 2.0983095169067383, 2.201604127883911, 2.2346043586730957, 2.2430291175842285, 2.275071620941162, 2.2782626152038574, 2.294647455215454, 2.351529598236084, 2.6157736778259277, 3.3646557331085205, 16.249480485916138]

GOOD = ['https://arweave.developerdao.com', 'https://ar-io.dev', 'https://permagate.io', 'https://arweave.net', 'https://aothecomputer.xyz', 'https://dwentz.site', 'https://adaconna.top', 'https://deknow.top', 'https://ario-testnet.us.nodefleet.org', 'https://exodusdiablo.xyz', 'https://iogate.co.uk', 'https://utkububa.xyz', 'https://aksamlan.xyz', 'https://iogate.uk', 'https://ariospeedwagon.com', 'https://stonkson.xyz', 'https://flashwayne.online', 'https://vrising.site', 'https://ozzcanx.xyz', 'https://ar.perplex.finance', 'https://g8way.io', 'https://apeweave.com', 'https://arweave.fllstck.dev', 'https://frostor.xyz', 'https://ademtor.xyz', 'https://vevivofficial.xyz', 'https://nodetitan.site', 'https://ar.riceinbucket.com', 'https://software0x.space', 'https://arioarioario.online', 'https://nodechecker.xyz', 'https://vn-sti.top', 'https://nodebiz.site', 'https://spectre01.site', 'https://flexibleee.xyz', 'https://kagithavlu.store', 'https://torku.xyz', 'https://anti-mage01.store', 'https://hlldrk.shop', 'https://elessardarken.xyz', 'https://khacasablanca.top', 'https://alexxis.store', 'https://bicem.xyz', 'https://arweaveblock.com', 'https://ivandivandelen.online', 'https://arnode.site', 'https://eaddaa.website', 'https://ar.alwaysbedream.dev', 'https://chocon.store', 'https://soulbreaker.xyz', 'https://nodehub.site', 'https://oshvank.site', 'https://kyotoorbust.site', 'https://nodebeta.site', 'https://snafyr.xyz', 'https://barburan.site', 'https://ar.kiranli.xyz', 'https://stilucky.top', 'https://koltigin.xyz', 'https://redwhiteconnect.xyz', 'https://adn79.pro', 'https://thanhapple.store', 'https://doflamingo.xyz', 'https://nodevip.site', 'https://ahmkahvalidator.xyz', 'https://sooneraydin.xyz', 'https://meocon.store', 'https://kiem-tran.tech', 'https://thd.io.vn', 'https://yusufaytn.xyz', 'https://blessingway.xyz', 'https://parafmax.site', 'https://murod.xyz', 'https://senzura.xyz', 'https://0xsav.xyz', 'https://svgtmrgl.xyz', 'https://ioar.xyz', 'https://nodezeta.site', 'https://liglow.com', 'https://alpt.autos', 'https://weaversnodes.info', 'https://mdbmesutmdb.shop', 'https://stajertestnetci.site', 'https://ariogateway.online', 'https://frogzz.xyz', 'https://regaret.xyz', 'https://canduesed.me', 'https://dnsarz.site', 'https://omersukrubektas.online', 'https://coshift.xyz', 'https://sakultarollapp.site', 'https://dtractusrpca.xyz', 'https://yakupgs.online', 'https://sowyer.xyz', 'https://pi314.xyz', 'https://recepgocmen.xyz', 'https://hexamz.tech', 'https://cmdexe.xyz', 'https://erenkurt.site', 'https://node69.site', 'https://ar.taskopru.xyz', 'https://fisneci.com', 'https://yolgezer55.xyz', 'https://aralper.xyz', 'https://mehteroglu.store', 'https://nodetester.com', 'https://zekkava.space', 'https://itsyalcin.xyz', 'https://practicers.xyz', 'https://mertorakk.xyz', 'https://hazmaniaxbt.online', 'https://rodruquez.online', 'https://mrciga.com', 'https://babayagax.online', 'https://alicans.online', 'https://kabaoglu.xyz', 'https://bambik.online', 'https://linaril.xyz', 'https://slatrokh.xyz', 'https://mustafakaya.xyz', 'https://sunkripto.site', 'https://0xyvz.xyz', 'https://campnode.xyz', 'https://karakartal.store', 'https://zionalc.online', 'https://bootstrap.icu', 'https://ykpbb.xyz', 'https://baristestnet.xyz', 'https://krayir.xyz', 'https://tefera.xyz', 'https://kunacan.xyz', 'https://ruangnode.xyz', 'https://zerolight.online', 'https://sarlos.site', 'https://grenimo.click', 'https://ar-arweave.xyz', 'https://kanan1.shop', 'https://bsckapp.store', 'https://ar.phuongvusolution.com', 'https://ahnetd.online', 'https://sametyuksel.xyz', 'https://kazazel.xyz', 'https://love4src.com', 'https://htonka.xyz', 'https://mrheracles.online', 'https://boramir.store', 'https://erenynk.xyz', 'https://chaintech.site', 'https://euraquilo.xyz', 'https://kingsharaldoperator.xyz', 'https://salakk.online', 'https://maclaurino.xyz', 'https://cyanalp.cfd', 'https://koniq.xyz', 'https://gatewaykeeper.net', 'https://crbaa.xyz', 'https://auquis.online', 'https://arceina.store', 'https://rollape.com.tr', 'https://darksunrayz.store', 'https://pentav.site', 'https://khaldrogo.site', 'https://mssnodes.xyz', 'https://lobibo.online', 'https://ar.bearnode.xyz', 'https://tekin86.online', 'https://vikanren.buzz', 'https://nodepepe.site', 'https://leechshop.com', 'https://treexyz.site', 'https://0xkullanici.online', 'https://mustafakara.space', 'https://yukovskibot.com', 'https://iblis.store', 'https://arweave.validator.wiki', 'https://vilenarios.com', 'https://ar.ilaybilge.xyz', 'https://ar.0xskyeagle.com', 'https://terminatormbd.com', 'https://merttemizer.xyz', 'https://mulosbron.xyz', 'https://rtmpsunucu.online', 'https://ar.tomris.xyz', 'https://adora0x0.xyz', 'https://arweave.auduge.com', 'https://ar.anyone.tech', 'https://araoai.com', 'https://flechemano.com', 'https://rikimaru111.site', 'https://2save.xyz', 'https://arbr.pro', 'https://ainodes.xyz', 'https://astrocosmos.website', 'https://didzcover.world', 'https://vnnode.top', 'https://ar.ionode.online', 'https://katsumii.xyz', 'https://ar-testnet.p10node.com', 'https://ar.owlstake.com', 'https://ar-node.megastake.org', 'https://arns-gateway.com', 'https://ario.dasamuka.xyz', 'https://ar.secret-network.xyz', 'https://teoteovivi.store', 'https://ar.satoshispalace.casino', 'https://imtran.site', 'https://wenairdropsir.store', 'https://kt10vip.online']

BAD = ['https://commissar.xyz', 'https://gisela-arg.xyz', 'https://sadas655.xyz', 'https://kenyaligeralt.xyz', 'https://ruyisu.net', 'https://0xmonyaaa.xyz', 'https://zirhelp.lol', 'https://gmajorscale.xyz', 'https://g8way.0rbit.co', 'https://misatoshi.pics', 'https://clyapp.xyz', 'https://dilsinay.online', 'https://secondtornado.xyz', 'https://mpsnode.online', 'https://gateway.getweave.org', 'https://comrat32.xyz', 'https://konobbeybackend.online', 'https://nodecoyote.xyz', 'https://sabrig1480.xyz', 'https://kingsharald.xyz', 'https://blockchainzk.website', 'https://vevivo.xyz', 'https://software0x.website', 'https://dasamuka.cloud', 'https://shapezero.xyz', 'https://bootstrap.lol', 'https://canduesed.xyz', 'https://nodeinvite.xyz', 'https://lethuan.xyz', 'https://bburan.xyz', 'https://velaryon.xyz', 'https://anch0r.com', 'https://thecoldblooded.online', 'https://moruehoca.online', 'https://cahil.store', 'https://dnsarz.wtf', 'https://rerererararags.store', 'https://validatorario.xyz', 'https://sefaaa.online', 'https://ahmkah.online', 'https://thecoldblooded.store', 'https://diafora.tech', 'https://berso.store', 'https://moruehoca.store', 'https://dilsinay2814.online', 'https://mutu.lol', 'https://cetinsefa.online', 'https://validatario.xyz', 'https://aantop.xyz', 'https://enesss.online', 'https://graski.xyz', 'https://wanr.top', 'https://arnode.cfd', 'https://aslanas01.xyz', 'https://jembutkucing.online', 'https://shadow39.online', 'https://jaxtothehell.xyz', 'https://parkdongfeng.store', 'https://khang.pro', 'https://r4dn.tech', 'https://darthlyrex.xyz', 'https://acanpolat.xyz', 'https://arnode.xyz', 'https://ar.qavurdagli.online', 'https://kahvenodes.online', 'https://prowsemre.online', 'https://nodevietnam.com', 'https://sygnblock.xyz', 'https://bodhiirozt.xyz', 'https://coinhunterstr.site', 'https://techvenience.net', 'https://apayro.xyz', 'https://anaraydinli.xyz', 'https://mrcetin03.store', 'https://arweave.ar', 'https://beyzako.xyz', 'https://cakonline.xyz', 'https://budavlebac.online', 'https://loriscant.site', 'https://0xsaitomo.xyz', 'https://neuweltgeld.xyz', 'https://arlogmein.xyz', 'https://arendor.xyz', 'https://ariozerowave.my.id', 'https://webraizo.online', 'https://xiaocloud.site', 'https://thekayz.xyz', 'https://captsuck.xyz', 'https://minhbear.xyz', 'https://Phuc.top', 'https://ibrahimdirik.xyz', 'https://sedat07.xyz', 'https://sulapan.com', 'https://maplesyrup-ario.my.id', 'https://herculesnode.shop', 'https://cayu7pa.xyz', 'https://mahcubyan.xyz', 'https://0xknowledge.store', 'https://testnetnodes.xyz', 'https://gurkanceltin.online', 'https://stevnode.site', 'https://ongtrong.xyz', 'https://kecil.tech', 'https://myphamalma.com', 'https://lanchiaw.xyz', 'https://getblock.store', 'https://emireray.shop', 'https://lobosqlinc.site', 'https://polkasub.site', 'https://shapezero.site', 'https://ario.stake.nexus', 'https://aoweave.tech', 'https://digitclone.online', 'https://lostgame.online', 'https://mutu.pro', 'https://ar-dreamnode.xyz', 'https://diafora.site', 'https://aleko0o.store']
