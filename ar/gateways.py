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
        for gw in tqdm.tqdm(new_gws[::-1], unit='gw'):
            _add(gw)
            write()
        for gw in tqdm.tqdm(stale_gws, unit='gw'):
            _pop(gw)
            _add(gw)
            write()

def update_best():
    for best in range(2):
        url = _pop(best)
        while _add(url) > best:
            url = _pop(best)
    write()

def update_one():
    idx = int(random.random() * random.random() * (len(GOOD)+len(BAD)))
    _add(_pop(idx))
    write()

def update_all():
    time_urls = []
    bad = []
    for url in tqdm.tqdm(BAD + GOOD, unit='gw'):
        try:
            time_urls.append([_make_gw_stat(url),url])
        except (ValueError, OSError):
            bad.append(url)
    time_urls.sort()
    TIMES = [time_url[0] for time_url in time_urls]
    GOOD = [time_url[1] for time_url in time_urls]
    BAD = bad
    write()

def write():
    with open(__file__,'r+t') as fh:
        content = fh.read()
        offset = content.rfind('TIMES = ')
        fh.seek(offset)
        fh.write('TIMES = ' + repr(TIMES) + '\n\nGOOD = ' + repr(GOOD) + '\n\nBAD = ' + repr(BAD))

TIMES = [0.337968111038208, 0.40737485885620117, 0.46909332275390625, 0.4843437671661377, 0.48905420303344727, 0.5034561157226562, 0.5188775062561035, 0.5417892932891846, 0.5796141624450684, 0.616631269454956, 0.6562955379486084, 0.6718001365661621, 0.7164595127105713, 0.728212833404541, 0.8221611976623535, 0.8830447196960449, 0.9044983386993408, 0.9427239894866943, 1.006380319595337, 1.0110702514648438, 1.0465033054351807, 1.080737590789795, 1.0903663635253906, 1.0970280170440674, 1.1274054050445557, 1.218712568283081, 1.222581386566162, 1.2272679805755615, 1.228510856628418, 1.2380480766296387, 1.2450933456420898, 1.2595255374908447, 1.2797462940216064, 1.2802326679229736, 1.290086030960083, 1.310441017150879, 1.3219738006591797, 1.3265392780303955, 1.3281874656677246, 1.3299939632415771, 1.3303048610687256, 1.330573320388794, 1.331223726272583, 1.34004545211792, 1.3533518314361572, 1.3573837280273438, 1.359532356262207, 1.3601064682006836, 1.3686192035675049, 1.4015867710113525, 1.4234812259674072, 1.431560754776001, 1.4317071437835693, 1.4328253269195557, 1.433014154434204, 1.4330394268035889, 1.433089017868042, 1.4331464767456055, 1.433192253112793, 1.433351755142212, 1.43339204788208, 1.43363356590271, 1.4344897270202637, 1.4402399063110352, 1.44252347946167, 1.4439563751220703, 1.4568543434143066, 1.4644553661346436, 1.466033697128296, 1.4856746196746826, 1.492830753326416, 1.4967834949493408, 1.5030393600463867, 1.5235424041748047, 1.5274326801300049, 1.528137445449829, 1.5327906608581543, 1.5331251621246338, 1.5332739353179932, 1.5353012084960938, 1.535315752029419, 1.5354139804840088, 1.5354788303375244, 1.535644769668579, 1.5357654094696045, 1.536149024963379, 1.5362606048583984, 1.5363311767578125, 1.5419373512268066, 1.5643811225891113, 1.5657742023468018, 1.57194185256958, 1.5767266750335693, 1.577059268951416, 1.5837934017181396, 1.590104341506958, 1.5915532112121582, 1.5979256629943848, 1.6044776439666748, 1.6155204772949219, 1.6295499801635742, 1.6295976638793945, 1.63090181350708, 1.631324052810669, 1.6375715732574463, 1.6375904083251953, 1.637617588043213, 1.6377649307250977, 1.6377668380737305, 1.6377699375152588, 1.6379165649414062, 1.637941837310791, 1.6379714012145996, 1.6382737159729004, 1.6385254859924316, 1.6390020847320557, 1.6393485069274902, 1.6396279335021973, 1.640028476715088, 1.6403429508209229, 1.6412651538848877, 1.6465485095977783, 1.6531102657318115, 1.6594843864440918, 1.6888072490692139, 1.699632167816162, 1.7002830505371094, 1.7101476192474365, 1.7162299156188965, 1.7198264598846436, 1.729722499847412, 1.7300982475280762, 1.7312464714050293, 1.738917350769043, 1.7400414943695068, 1.7405626773834229, 1.7407221794128418, 1.7412080764770508, 1.7418289184570312, 1.750565767288208, 1.7578277587890625, 1.764829397201538, 1.765230655670166, 1.7687256336212158, 1.7729992866516113, 1.7783148288726807, 1.782956600189209, 1.792771339416504, 1.7953894138336182, 1.824474811553955, 1.8257575035095215, 1.8311879634857178, 1.8423566818237305, 1.8429858684539795, 1.8429889678955078, 1.8432550430297852, 1.84372878074646, 1.8506081104278564, 1.855743408203125, 1.9013891220092773, 1.9156596660614014, 1.9283111095428467, 1.9450018405914307, 1.9451251029968262, 1.9524712562561035, 1.992560863494873, 1.9972012042999268, 2.006603717803955, 2.0472569465637207, 2.0540661811828613, 2.080612897872925, 2.126232147216797, 2.150080919265747, 2.1618635654449463, 2.2520956993103027, 2.25260329246521, 2.2562413215637207, 2.3155364990234375, 2.3413760662078857, 2.4138829708099365, 2.4140408039093018, 2.4477367401123047, 2.4576575756073, 2.458150625228882, 2.4641287326812744, 2.555699110031128, 2.5598835945129395, 2.5605995655059814, 2.603853464126587, 2.6054956912994385, 2.613574266433716, 2.6318981647491455, 2.6599159240722656, 2.664189100265503, 2.704454183578491, 2.7083487510681152, 2.834357976913452, 2.8670153617858887, 2.8841164112091064, 3.0070667266845703, 3.0706307888031006, 3.1745388507843018, 3.4082820415496826, 4.300439834594727, 5.630784034729004, 6.143873929977417, 7.202648162841797, 7.9720845222473145, 16.405986785888672, 18.11179757118225, 18.431824684143066]

GOOD = ['https://ar-io.dev', 'https://arweave.net', 'https://0xsaitomo.xyz', 'https://exodusdiablo.xyz', 'https://cahil.store', 'https://iogate.uk', 'https://aksamlan.xyz', 'https://moruehoca.online', 'https://acanpolat.xyz', 'https://ario-testnet.us.nodefleet.org', 'https://velaryon.xyz', 'https://kahvenodes.online', 'https://ozzcanx.xyz', 'https://iogate.co.uk', 'https://apeweave.com', 'https://bodhiirozt.xyz', 'https://arweave.developerdao.com', 'https://ariospeedwagon.com', 'https://frostor.xyz', 'https://aoweave.tech', 'https://dwentz.site', 'https://thd.io.vn', 'https://permagate.io', 'https://doflamingo.xyz', 'https://arweave.auduge.com', 'https://mrcetin03.store', 'https://adaconna.top', 'https://mustafakaya.xyz', 'https://arnode.xyz', 'https://vrising.site', 'https://kunacan.xyz', 'https://arweaveblock.com', 'https://chaintech.site', 'https://arweave.ar', 'https://digitclone.online', 'https://cmdexe.xyz', 'https://arweave.fllstck.dev', 'https://hexamz.tech', 'https://ykpbb.xyz', 'https://redwhiteconnect.xyz', 'https://sametyuksel.xyz', 'https://darthlyrex.xyz', 'https://kingsharald.xyz', 'https://loriscant.site', 'https://babayagax.online', 'https://coshift.xyz', 'https://flechemano.com', 'https://erenkurt.site', 'https://zerolight.online', 'https://rerererararags.store', 'https://maclaurino.xyz', 'https://regaret.xyz', 'https://liglow.com', 'https://kagithavlu.store', 'https://yakupgs.online', 'https://aslanas01.xyz', 'https://frogzz.xyz', 'https://alexxis.store', 'https://canduesed.xyz', 'https://aleko0o.store', 'https://mehteroglu.store', 'https://snafyr.xyz', 'https://kiem-tran.tech', 'https://0xsav.xyz', 'https://ivandivandelen.online', 'https://mrheracles.online', 'https://anch0r.com', 'https://enesss.online', 'https://anaraydinli.xyz', 'https://murod.xyz', 'https://practicers.xyz', 'https://lanchiaw.xyz', 'https://parafmax.site', 'https://zionalc.online', 'https://vikanren.buzz', 'https://cayu7pa.xyz', 'https://rodruquez.online', 'https://ademtor.xyz', 'https://cyanalp.cfd', 'https://ar.taskopru.xyz', 'https://senzura.xyz', 'https://flexibleee.xyz', 'https://boramir.store', 'https://mrciga.com', 'https://bootstrap.lol', 'https://prowsemre.online', 'https://krayir.xyz', 'https://nodehub.site', 'https://nodepepe.site', 'https://love4src.com', 'https://mdbmesutmdb.shop', 'https://webraizo.online', 'https://mertorakk.xyz', 'https://erenynk.xyz', 'https://zekkava.space', 'https://ahnetd.online', 'https://campnode.xyz', 'https://sowyer.xyz', 'https://weaversnodes.info', 'https://alpt.autos', 'https://lostgame.online', 'https://dtractusrpca.xyz', 'https://adn79.pro', 'https://yolgezer55.xyz', 'https://stajertestnetci.site', 'https://htonka.xyz', 'https://kanan1.shop', 'https://herculesnode.shop', 'https://deknow.top', 'https://svgtmrgl.xyz', 'https://blockchainzk.website', 'https://arendor.xyz', 'https://coinhunterstr.site', 'https://0xyvz.xyz', 'https://slatrokh.xyz', 'https://arweave.validator.wiki', 'https://mustafakara.space', 'https://g8way.io', 'https://nodechecker.xyz', 'https://rikimaru111.site', 'https://ar.bearnode.xyz', 'https://kabaoglu.xyz', 'https://0xkullanici.online', 'https://sefaaa.online', 'https://shapezero.xyz', 'https://linaril.xyz', 'https://stevnode.site', 'https://nodebiz.site', 'https://alicans.online', 'https://nodetester.com', 'https://crbaa.xyz', 'https://0xknowledge.store', 'https://vevivo.xyz', 'https://kazazel.xyz', 'https://arbr.pro', 'https://elessardarken.xyz', 'https://beyzako.xyz', 'https://koniq.xyz', 'https://ar.anyone.tech', 'https://iblis.store', 'https://darksunrayz.store', 'https://testnetnodes.xyz', 'https://arceina.store', 'https://aralper.xyz', 'https://salakk.online', 'https://torku.xyz', 'https://Phuc.top', 'https://leechshop.com', 'https://adora0x0.xyz', 'https://khaldrogo.site', 'https://ar.riceinbucket.com', 'https://kyotoorbust.site', 'https://arnode.site', 'https://node69.site', 'https://spectre01.site', 'https://validatorario.xyz', 'https://mulosbron.xyz', 'https://ar.kiranli.xyz', 'https://khacasablanca.top', 'https://sunkripto.site', 'https://tekin86.online', 'https://rtmpsunucu.online', 'https://thecoldblooded.online', 'https://ruangnode.xyz', 'https://rollape.com.tr', 'https://auquis.online', 'https://omersukrubektas.online', 'https://ahmkah.online', 'https://mssnodes.xyz', 'https://soulbreaker.xyz', 'https://ar.0xskyeagle.com', 'https://bicem.xyz', 'https://thekayz.xyz', 'https://maplesyrup-ario.my.id', 'https://ariogateway.online', 'https://yukovskibot.com', 'https://ar.tomris.xyz', 'https://katsumii.xyz', 'https://sakultarollapp.site', 'https://astrocosmos.website', 'https://nodetitan.site', 'https://ar.satoshispalace.casino', 'https://ar-testnet.p10node.com', 'https://araoai.com', 'https://ar.qavurdagli.online', 'https://karakartal.store', 'https://nodebeta.site', 'https://nodevip.site', 'https://dasamuka.cloud', 'https://koltigin.xyz', 'https://ar.owlstake.com', 'https://euraquilo.xyz', 'https://yusufaytn.xyz', 'https://ar.ilaybilge.xyz', 'https://anti-mage01.store', 'https://chocon.store', 'https://arns-gateway.com', 'https://aantop.xyz', 'https://ar-node.megastake.org', 'https://2save.xyz', 'https://imtran.site', 'https://ar.secret-network.xyz', 'https://fisneci.com', 'https://software0x.website', 'https://ainodes.xyz', 'https://ar.ionode.online', 'https://vilenarios.com', 'https://nodezeta.site', 'https://meocon.store', 'https://thanhapple.store', 'https://kt10vip.online']

BAD = ['https://dnsarz.wtf', 'https://sedat07.xyz', 'https://vn-sti.top', 'https://ioar.xyz', 'https://tefera.xyz', 'https://commissar.xyz', 'https://flashwayne.online', 'https://sooneraydin.xyz', 'https://getblock.store', 'https://gurkanceltin.online', 'https://aothecomputer.xyz', 'https://itsyalcin.xyz', 'https://blessingway.xyz', 'https://jaxtothehell.xyz', 'https://bsckapp.store', 'https://gisela-arg.xyz', 'https://sadas655.xyz', 'https://graski.xyz', 'https://treexyz.site', 'https://ar-arweave.xyz', 'https://pentav.site', 'https://bburan.xyz', 'https://mahcubyan.xyz', 'https://ibrahimdirik.xyz', 'https://shadow39.online', 'https://techvenience.net', 'https://kecil.tech', 'https://captsuck.xyz', 'https://kenyaligeralt.xyz', 'https://ruyisu.net', 'https://lobosqlinc.site', 'https://grenimo.click', 'https://0xmonyaaa.xyz', 'https://oshvank.site', 'https://zirhelp.lol', 'https://diafora.site', 'https://sarlos.site', 'https://ariozerowave.my.id', 'https://ar.phuongvusolution.com', 'https://stilucky.top', 'https://khang.pro', 'https://ar-dreamnode.xyz', 'https://myphamalma.com', 'https://cakonline.xyz', 'https://baristestnet.xyz', 'https://gmajorscale.xyz', 'https://g8way.0rbit.co', 'https://nodevietnam.com', 'https://recepgocmen.xyz', 'https://minhbear.xyz', 'https://neuweltgeld.xyz', 'https://teoteovivi.store', 'https://misatoshi.pics', 'https://sygnblock.xyz', 'https://emireray.shop', 'https://clyapp.xyz', 'https://ongtrong.xyz', 'https://dilsinay.online', 'https://mutu.pro', 'https://secondtornado.xyz', 'https://mpsnode.online', 'https://apayro.xyz', 'https://arnode.cfd', 'https://pi314.xyz', 'https://sulapan.com', 'https://ario.stake.nexus', 'https://gateway.getweave.org', 'https://budavlebac.online', 'https://comrat32.xyz', 'https://merttemizer.xyz', 'https://vnnode.top', 'https://polkasub.site', 'https://konobbeybackend.online', 'https://hazmaniaxbt.online', 'https://jembutkucing.online', 'https://sabrig1480.xyz', 'https://terminatormbd.com', 'https://nodecoyote.xyz', 'https://nodeinvite.xyz', 'https://lethuan.xyz', 'https://parkdongfeng.store', 'https://r4dn.tech', 'https://wanr.top', 'https://arlogmein.xyz', 'https://xiaocloud.site', 'https://utkububa.xyz', 'https://hlldrk.shop']
