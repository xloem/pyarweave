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
    '0eRcI5PpUQGIDcBGTPCcANkUkgY85a1VGf0o7Y-q01o',
    hashlib.sha512,
    '7a240f64db4264370ad371a76837ac837f5bee9756bea793c5c27bae04e98e3d853c24c031ba350e3006ea8c83c2c93ec0d6549dca51970d4e12add24fd44b2f'
]

def fetch_from_registry(cu = None, process_id = None, raw = False):
    import ao, json
    cu = cu or ao.cu()
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
    content = requests.get(url + '/' + REF[0], timeout=15).content
    duration = time.time() - start
    if REF[1](content).hexdigest() != REF[2]:
        raise ValueError('Incorrect content')
    return duration

def _add(gw):
    try:
        time = _make_gw_stat(gw)
    except (ValueError, OSError):
        BAD.append(gw)
        return len(GOOD) + len(BAD) - 1
    else:
        idx = bisect.bisect(TIMES, time)
        TIMES.insert(idx, time)
        GOOD.insert(idx, gw)
        return idx

def _pop(idx_or_url):
    if type(idx_or_url) is int:
        if idx_or_url > len(GOOD):
            url = BAD.pop(idx_or_url)
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
            while _add(url) > best:
                pbar.set_description('no longer best: ' + url, refresh=False)
                url = _pop(best)
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

TIMES = [0.3588886260986328, 0.6140305995941162, 0.6808271408081055, 0.6943833827972412, 0.6974203586578369, 0.7081055641174316, 0.7204713821411133, 0.7279481887817383, 0.7333757877349854, 0.7783756256103516, 0.8413012027740479, 0.8468437194824219, 0.8554410934448242, 0.8633933067321777, 0.8699989318847656, 0.8750181198120117, 0.8968000411987305, 0.9419386386871338, 1.1576354503631592, 1.1779334545135498, 1.2307734489440918, 1.2351744174957275, 1.242264986038208, 1.2537181377410889, 1.2717642784118652, 1.2964394092559814, 1.2972934246063232, 1.314668893814087, 1.3173630237579346, 1.3420963287353516, 1.342766523361206, 1.3509409427642822, 1.3597443103790283, 1.370854139328003, 1.3779575824737549, 1.379502773284912, 1.3815858364105225, 1.4000558853149414, 1.4289298057556152, 1.4339659214019775, 1.4426167011260986, 1.45225191116333, 1.4548330307006836, 1.460364580154419, 1.4617726802825928, 1.4660286903381348, 1.4761724472045898, 1.478792667388916, 1.490917682647705, 1.498258352279663, 1.5751903057098389, 1.5826685428619385, 1.585245132446289, 1.5959112644195557, 1.5988044738769531, 1.6027426719665527, 1.6120455265045166, 1.613534688949585, 1.6245644092559814, 1.6268081665039062, 1.6331000328063965, 1.634918212890625, 1.645524501800537, 1.6494312286376953, 1.6552143096923828, 1.6570823192596436, 1.6586816310882568, 1.6691575050354004, 1.6703011989593506, 1.6742827892303467, 1.69081711769104, 1.6908574104309082, 1.6986217498779297, 1.6999173164367676, 1.701256513595581, 1.7120890617370605, 1.7251689434051514, 1.7301690578460693, 1.735001564025879, 1.7369577884674072, 1.7411715984344482, 1.7413442134857178, 1.7649750709533691, 1.7655572891235352, 1.767249345779419, 1.7739994525909424, 1.778193473815918, 1.77988600730896, 1.7903621196746826, 1.8009843826293945, 1.801403284072876, 1.8075203895568848, 1.8078525066375732, 1.8105978965759277, 1.81807541847229, 1.8191447257995605, 1.8195626735687256, 1.8268358707427979, 1.8348371982574463, 1.8399474620819092, 1.8408689498901367, 1.851416826248169, 1.8518130779266357, 1.8578739166259766, 1.859971284866333, 1.8663556575775146, 1.8751370906829834, 1.881814956665039, 1.8991100788116455, 1.9016647338867188, 1.9025559425354004, 1.9140493869781494, 1.916485071182251, 1.917877435684204, 1.9192042350769043, 1.9194347858428955, 1.924820899963379, 1.946824550628662, 1.95023775100708, 1.9545269012451172, 1.9598534107208252, 1.9688050746917725, 1.9729456901550293, 1.9815890789031982, 1.9875390529632568, 1.993901014328003, 2.0064353942871094, 2.0233898162841797, 2.0259313583374023, 2.0261974334716797, 2.031761407852173, 2.039280652999878, 2.0433943271636963, 2.0448524951934814, 2.050966262817383, 2.055460214614868, 2.0560593605041504, 2.058293581008911, 2.0614798069000244, 2.0622293949127197, 2.0678341388702393, 2.0680179595947266, 2.0776209831237793, 2.090484380722046, 2.0905399322509766, 2.1040427684783936, 2.1125619411468506, 2.113784074783325, 2.1191141605377197, 2.1237120628356934, 2.135700225830078, 2.1373867988586426, 2.143217086791992, 2.1554365158081055, 2.1578526496887207, 2.1588096618652344, 2.16326904296875, 2.168450355529785, 2.1881933212280273, 2.190164804458618, 2.196678400039673, 2.1983413696289062, 2.198819637298584, 2.2157273292541504, 2.2175755500793457, 2.2202343940734863, 2.2232329845428467, 2.230755567550659, 2.2335445880889893, 2.2378761768341064, 2.2382895946502686, 2.239535331726074, 2.2444541454315186, 2.2523956298828125, 2.264345645904541, 2.2647368907928467, 2.2744877338409424, 2.281888484954834, 2.2867751121520996, 2.308098793029785, 2.3125839233398438, 2.3185768127441406, 2.3195977210998535, 2.330136775970459, 2.335402488708496, 2.339385747909546, 2.347304105758667, 2.3549342155456543, 2.363646984100342, 2.370797872543335, 2.3944289684295654, 2.4080934524536133, 2.4182939529418945, 2.428863048553467, 2.4516639709472656, 2.477508783340454, 2.4833908081054688, 2.513429641723633, 2.5326366424560547, 2.5522894859313965, 2.638551712036133, 2.641242265701294, 2.6990787982940674, 2.8219428062438965, 2.825028657913208, 2.844836950302124, 2.8571255207061768, 2.8766517639160156, 2.877556800842285, 2.9191129207611084, 3.1271376609802246, 3.3365631103515625, 3.347350835800171, 3.3917629718780518, 3.4810378551483154, 3.9887936115264893, 4.074273347854614, 4.195009469985962, 4.398658275604248, 5.925209045410156, 6.899348735809326, 7.23184871673584, 7.577540397644043, 17.34520149230957]

GOOD = ['https://arweave.net', 'https://acanpolat.xyz', 'https://utkububa.xyz', 'https://moruehoca.online', 'https://ario-testnet.us.nodefleet.org', 'https://iogate.co.uk', 'https://adaconna.top', 'https://arweave.developerdao.com', 'https://flashwayne.online', 'https://ozzcanx.xyz', 'https://cahil.store', 'https://velaryon.xyz', 'https://exodusdiablo.xyz', 'https://iogate.uk', 'https://0xsaitomo.xyz', 'https://vrising.site', 'https://aksamlan.xyz', 'https://bodhiirozt.xyz', 'https://deknow.top', 'https://sowyer.xyz', 'https://emireray.shop', 'https://soulbreaker.xyz', 'https://kunacan.xyz', 'https://flechemano.com', 'https://snafyr.xyz', 'https://babayagax.online', 'https://campnode.xyz', 'https://senzura.xyz', 'https://ibrahimdirik.xyz', 'https://leechshop.com', 'https://alpt.autos', 'https://ar.anyone.tech', 'https://zekkava.space', 'https://frostor.xyz', 'https://yusufaytn.xyz', 'https://ahmkah.online', 'https://stajertestnetci.site', 'https://didzcover.world', 'https://erenkurt.site', 'https://apeweave.com', 'https://kanan1.shop', 'https://arweaveblock.com', 'https://vevivofficial.xyz', 'https://rodruquez.online', 'https://eaddaa.website', 'https://ariospeedwagon.com', 'https://torku.xyz', 'https://terminatormbd.com', 'https://doflamingo.xyz', 'https://coshift.xyz', 'https://testnetnodes.xyz', 'https://erenynk.xyz', 'https://yolgezer55.xyz', 'https://karakartal.store', 'https://shapezero.xyz', 'https://arweave.fllstck.dev', 'https://love4src.com', 'https://dwentz.site', 'https://arceina.store', 'https://koniq.xyz', 'https://mrcetin03.store', 'https://parafmax.site', 'https://mrciga.com', 'https://sametyuksel.xyz', 'https://liglow.com', 'https://sakultarollapp.site', 'https://frogzz.xyz', 'https://digitclone.online', 'https://chocon.store', 'https://validatorario.xyz', 'https://beyzako.xyz', 'https://ademtor.xyz', 'https://hexamz.tech', 'https://spectre01.site', 'https://flexibleee.xyz', 'https://canduesed.xyz', 'https://anch0r.com', 'https://anti-mage01.store', 'https://g8way.io', 'https://kyotoorbust.site', 'https://ykpbb.xyz', 'https://weaversnodes.info', 'https://mssnodes.xyz', 'https://alexxis.store', 'https://sefaaa.online', 'https://mertorakk.xyz', 'https://kabaoglu.xyz', 'https://lostgame.online', 'https://redwhiteconnect.xyz', 'https://cmdexe.xyz', 'https://dtractusrpca.xyz', 'https://ar.kiranli.xyz', 'https://nodebeta.site', 'https://nodechecker.xyz', 'https://aralper.xyz', 'https://rikimaru111.site', 'https://kagithavlu.store', 'https://0xyvz.xyz', 'https://nodezeta.site', 'https://bicem.xyz', 'https://coinhunterstr.site', 'https://ar.bearnode.xyz', 'https://kazazel.xyz', 'https://arnode.site', 'https://prowsemre.online', 'https://baristestnet.xyz', 'https://mehteroglu.store', 'https://darksunrayz.store', 'https://yakupgs.online', 'https://ruangnode.xyz', 'https://darthlyrex.xyz', 'https://node69.site', 'https://zerolight.online', 'https://herculesnode.shop', 'https://Phuc.top', 'https://arweave.auduge.com', 'https://ar.taskopru.xyz', 'https://kiem-tran.tech', 'https://crbaa.xyz', 'https://webraizo.online', 'https://aantop.xyz', 'https://arweave.ar', 'https://aslanas01.xyz', 'https://software0x.space', 'https://htonka.xyz', 'https://stevnode.site', 'https://practicers.xyz', 'https://recepgocmen.xyz', 'https://vikanren.buzz', 'https://0xkullanici.online', 'https://grenimo.click', 'https://ariogateway.online', 'https://cyanalp.cfd', 'https://bsckapp.store', 'https://ivandivandelen.online', 'https://ioar.xyz', 'https://boramir.store', 'https://cayu7pa.xyz', 'https://lanchiaw.xyz', 'https://itsyalcin.xyz', 'https://nodebiz.site', 'https://oshvank.site', 'https://regaret.xyz', 'https://0xsav.xyz', 'https://enesss.online', 'https://sunkripto.site', 'https://mdbmesutmdb.shop', 'https://ar.phuongvusolution.com', 'https://zionalc.online', 'https://nodetitan.site', 'https://nodevip.site', 'https://ar-arweave.xyz', 'https://bburan.xyz', 'https://rtmpsunucu.online', 'https://mutu.pro', 'https://ar.tomris.xyz', 'https://chaintech.site', 'https://anaraydinli.xyz', 'https://maclaurino.xyz', 'https://nodepepe.site', 'https://aleko0o.store', 'https://elessardarken.xyz', 'https://sarlos.site', 'https://2save.xyz', 'https://loriscant.site', 'https://adn79.pro', 'https://maplesyrup-ario.my.id', 'https://nodehub.site', 'https://dnsarz.wtf', 'https://arweave.validator.wiki', 'https://salakk.online', 'https://jaxtothehell.xyz', 'https://slatrokh.xyz', 'https://tekin86.online', 'https://merttemizer.xyz', 'https://permagate.io', 'https://blessingway.xyz', 'https://krayir.xyz', 'https://iblis.store', 'https://khacasablanca.top', 'https://koltigin.xyz', 'https://0xknowledge.store', 'https://ar.owlstake.com', 'https://ar.ilaybilge.xyz', 'https://omersukrubektas.online', 'https://dasamuka.cloud', 'https://ahnetd.online', 'https://murod.xyz', 'https://ar.ionode.online', 'https://alicans.online', 'https://thd.io.vn', 'https://bootstrap.lol', 'https://mrheracles.online', 'https://ar.satoshispalace.casino', 'https://sooneraydin.xyz', 'https://svgtmrgl.xyz', 'https://ar-io.dev', 'https://adora0x0.xyz', 'https://ar-testnet.p10node.com', 'https://katsumii.xyz', 'https://rollape.com.tr', 'https://tefera.xyz', 'https://sulapan.com', 'https://arns-gateway.com', 'https://yukovskibot.com', 'https://ar.secret-network.xyz', 'https://thecoldblooded.online', 'https://astrocosmos.website', 'https://pentav.site', 'https://treexyz.site', 'https://diafora.site', 'https://ar.0xskyeagle.com', 'https://imtran.site', 'https://khaldrogo.site', 'https://ar-node.megastake.org', 'https://fisneci.com', 'https://vilenarios.com', 'https://araoai.com', 'https://aoweave.tech', 'https://wanr.top', 'https://auquis.online', 'https://rerererararags.store', 'https://ainodes.xyz', 'https://kt10vip.online']

BAD = ['https://sedat07.xyz', 'https://vn-sti.top', 'https://commissar.xyz', 'https://getblock.store', 'https://gurkanceltin.online', 'https://aothecomputer.xyz', 'https://gisela-arg.xyz', 'https://sadas655.xyz', 'https://graski.xyz', 'https://mahcubyan.xyz', 'https://shadow39.online', 'https://techvenience.net', 'https://kecil.tech', 'https://captsuck.xyz', 'https://kenyaligeralt.xyz', 'https://ruyisu.net', 'https://lobosqlinc.site', 'https://0xmonyaaa.xyz', 'https://zirhelp.lol', 'https://ariozerowave.my.id', 'https://stilucky.top', 'https://khang.pro', 'https://ar-dreamnode.xyz', 'https://myphamalma.com', 'https://cakonline.xyz', 'https://gmajorscale.xyz', 'https://g8way.0rbit.co', 'https://nodevietnam.com', 'https://minhbear.xyz', 'https://neuweltgeld.xyz', 'https://teoteovivi.store', 'https://misatoshi.pics', 'https://sygnblock.xyz', 'https://clyapp.xyz', 'https://ongtrong.xyz', 'https://dilsinay.online', 'https://secondtornado.xyz', 'https://mpsnode.online', 'https://apayro.xyz', 'https://arnode.cfd', 'https://pi314.xyz', 'https://gateway.getweave.org', 'https://budavlebac.online', 'https://comrat32.xyz', 'https://vnnode.top', 'https://polkasub.site', 'https://hazmaniaxbt.online', 'https://r4dn.tech', 'https://xiaocloud.site', 'https://ario.stake.nexus', 'https://jembutkucing.online', 'https://arendor.xyz', 'https://nodeinvite.xyz', 'https://konobbeybackend.online', 'https://hlldrk.shop', 'https://nodecoyote.xyz', 'https://sabrig1480.xyz', 'https://parkdongfeng.store', 'https://arlogmein.xyz', 'https://lethuan.xyz', 'https://kahvenodes.online', 'https://mustafakaya.xyz', 'https://arnode.xyz', 'https://kingsharald.xyz', 'https://blockchainzk.website', 'https://mustafakara.space', 'https://linaril.xyz', 'https://nodetester.com', 'https://vevivo.xyz', 'https://arbr.pro', 'https://ar.riceinbucket.com', 'https://mulosbron.xyz', 'https://thekayz.xyz', 'https://ar.qavurdagli.online', 'https://euraquilo.xyz', 'https://software0x.website', 'https://meocon.store', 'https://thanhapple.store']
