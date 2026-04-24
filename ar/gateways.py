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

REF = {
    'algorithm': hashlib.sha512,
    'requests': [{
        'name': '100k ditem',
        'path': 'hOll2P-jMFJ4GX-7bp51ZBypeJoTyEXFxSJLquaCR_s', 
        'payload': None,
        'headers': {},#dict(Range='bytes=-65536'),
        'size': 101323,
        'hexdigest': 'a78261e6c930d335602b77ca02ff032e9fbfc1a5efeb3feb80707716c088f639783a7d0d691de68325e8d60918d66cc78f12dec9d53170f499dd6a5d77f4cd61',
    #}, {
    #    'name': 'unconfirmed graphql tx',
    #    'path': 'graphql',
    #    'headers': {'Content-Type': 'application/json'},
    #    'payload': json.dumps({'operationName':None,'query':'query{transactions(sort:HEIGHT_DESC,first:1){edges{node{block{id height}}}}}','variables':{}}),
    #    'size': len('{"data":{"transactions":{"edges":[{"node":{"block":null}}]}}}\n'),
    #    'hexdigest': hashlib.sha512('{"data":{"transactions":{"edges":[{"node":{"block":null}}]}}}\n'.encode()).hexdigest(),
    }, {
        'name': 'block/current',
        'path': 'block/current',
        'verify': json.loads,
    #}, {
    #    'name': 'binary genesis block',
    #    'path': 'block2/height/0',
    #    'size': 11189,
    #    'hexdigest': '70a8b881099b4ccb65a03d74ee95e010eb56b6e4fbfb4f10f6e1274012cbd46ce2f9f1e9dc684c3035bdbd58ac08604b11283a7fd847a1e0df92f59881bcb338',
    }]
}

def fetch_from_registry(cu = None, process_id = None, raw = False):
    import ao, json
    cu = cu or ao.cu(host='https://cu.ardrive.io')
    process_id = process_id or ao.AR_IO_MAINNET_PROCESS_ID
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
        if request.get('payload') is None:
            response = requests.get(url + '/' + request['path'], headers=request.get('headers'), timeout=30, stream='size' in request)
        else:
            response = requests.post(url + '/' + request['path'], data = request['payload'], headers=request.get('headers'), timeout=15, stream='size' in request)
        if 'size' in request:
            with response:
                response.raise_for_status()
                for chunk in response.iter_content(request['size']):
                    content += chunk
                    if len(content) >= request['size']:
                        break
            if len(content) < request['size']:
                raise ValueError('Short content', request['name'])
        else:
            content = response.content
        duration = time.time() - start
        if request.get('hexdigest') is not None and REF['algorithm'](content[:request['size']]).hexdigest() != request['hexdigest']:
            raise ValueError('Incorrect content', request['name'], content)
        if 'verify' in request:
            assert request['verify'](content)
    return duration

def _add(gw):
    try:
        time = _make_gw_stat(gw)
    except (ValueError, OSError) as exc:
        import logging
        logging.exception(exc)
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
    import tqdm
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
    import tqdm
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
    import tqdm
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
    from ar.utils import FileLock
    with open(__file__,'r+t') as fh, FileLock(fh):
        content = fh.read()
        start = content.rfind('TIMES = ')
        end = content.find('\n', content.find('BAD = ', start))
        fh.seek(start)
        fh.write('TIMES = ' + repr(TIMES) + '\n\nGOOD = ' + repr(GOOD) + '\n\nBAD = ' + repr(BAD) + content[end:])
        fh.truncate()

TIMES = [2.55309796333313, 2.9331510066986084, 3.0982089042663574, 3.1769399642944336, 3.268369197845459, 3.4501261711120605, 3.576903820037842, 3.6028172969818115, 3.6542789936065674, 3.655033826828003, 3.6749377250671387, 3.704522132873535, 3.706089735031128, 3.7404720783233643, 3.7914161682128906, 3.8004751205444336, 3.8034539222717285, 3.822169303894043, 3.8259410858154297, 3.84104585647583, 3.855029821395874, 3.9295010566711426, 3.933932065963745, 4.0009191036224365, 4.0206382274627686, 4.025936603546143, 4.029895067214966, 4.03839373588562, 4.06633734703064, 4.066542863845825, 4.078831911087036, 4.109850883483887, 4.113708972930908, 4.117843151092529, 4.15199089050293, 4.164582967758179, 4.1919989585876465, 4.197399616241455, 4.211139678955078, 4.225982666015625, 4.228419065475464, 4.234654188156128, 4.235309600830078, 4.239546298980713, 4.243725299835205, 4.25998592376709, 4.272213459014893, 4.274951219558716, 4.302234888076782, 4.309724569320679, 4.353245973587036, 4.37325644493103, 4.375192642211914, 4.381978988647461, 4.393394231796265, 4.429666757583618, 4.44851016998291, 4.46321702003479, 4.485411167144775, 4.503814458847046, 4.545546770095825, 4.547702074050903, 4.553371906280518, 4.573748350143433, 4.595908164978027, 4.601937294006348, 4.606337547302246, 4.6271891593933105, 4.64933705329895, 4.657081127166748, 4.6709885597229, 4.676004648208618, 4.677426815032959, 4.694388151168823, 4.706185340881348, 4.706930160522461, 4.753223419189453, 4.761251449584961, 4.780768871307373, 4.787178039550781, 4.821641206741333, 4.83866024017334, 4.852686882019043, 4.858232498168945, 4.867813587188721, 4.874958038330078, 4.887440204620361, 4.888430595397949, 4.891639947891235, 4.893490314483643, 4.8938517570495605, 4.925847768783569, 4.941778182983398, 4.9527246952056885, 4.9779675006866455, 4.9906275272369385, 4.99392557144165, 4.998687505722046, 5.010035753250122, 5.018902063369751, 5.019346714019775, 5.056426286697388, 5.067592620849609, 5.0784032344818115, 5.087796449661255, 5.088294744491577, 5.116597652435303, 5.176852703094482, 5.178469657897949, 5.255886793136597, 5.265484094619751, 5.278752326965332, 5.287020206451416, 5.30188250541687, 5.319982528686523, 5.439517021179199, 5.447400093078613, 5.496495246887207, 5.505852699279785, 5.536272048950195, 5.5694310665130615, 5.5837953090667725, 5.627244234085083, 5.658000946044922, 5.675129175186157, 5.684577703475952, 5.838748455047607, 5.871300458908081, 5.876508951187134, 5.98088264465332, 5.987177610397339, 6.036043405532837, 6.05341911315918, 6.099895238876343, 6.117724418640137, 6.1676740646362305, 6.170867443084717, 6.254157543182373, 6.268298625946045, 6.276728391647339, 6.285614252090454, 6.326174020767212, 6.327712059020996, 6.33858585357666, 6.367939233779907, 6.390817165374756, 6.396712779998779, 6.450952529907227, 6.451769590377808, 6.538140535354614, 6.579241037368774, 6.60082221031189, 6.61196756362915, 6.641460180282593, 6.648691654205322, 6.674387216567993, 6.679547548294067, 6.714945077896118, 6.7380897998809814, 6.766658306121826, 6.7738494873046875, 6.779365062713623, 6.819169282913208, 6.821996212005615, 6.855889320373535, 6.866448163986206, 6.9768359661102295, 7.052168607711792, 7.059497356414795, 7.060353755950928, 7.119484186172485, 7.134633779525757, 7.281705856323242, 7.294416666030884, 7.33299994468689, 7.355138063430786, 7.356434106826782, 7.422155380249023, 7.473594903945923, 7.517584800720215, 7.524485111236572, 7.645712614059448, 7.69228982925415, 7.71770715713501, 7.733942270278931, 7.739071607589722, 7.753338098526001, 7.806250095367432, 7.900461435317993, 7.973535537719727, 7.974584341049194, 8.017683029174805, 8.029364824295044, 8.137514591217041, 8.14749550819397, 8.162371635437012, 8.186532258987427, 8.187926769256592, 8.201228618621826, 8.214285135269165, 8.219547033309937, 8.226672410964966, 8.231282949447632, 8.26104998588562, 8.273366928100586, 8.27693247795105, 8.281429529190063, 8.281601667404175, 8.28658151626587, 8.300153017044067, 8.312092781066895, 8.323409795761108, 8.329004764556885, 8.375431060791016, 8.380737543106079, 8.382413148880005, 8.384626388549805, 8.391039371490479, 8.410744190216064, 8.423341274261475, 8.477455854415894, 8.50146484375, 8.540330410003662, 8.57674241065979, 8.583991527557373, 8.587204217910767, 8.587820768356323, 8.592180967330933, 8.639113426208496, 8.709239721298218, 8.786723613739014, 8.788578033447266, 8.798254013061523, 8.802932024002075, 8.872026681900024, 8.893166303634644, 8.921046257019043, 8.985531330108643, 8.988268375396729, 8.988655805587769, 9.003134965896606, 9.004589796066284, 9.00496244430542, 9.010664701461792, 9.051387071609497, 9.110295295715332, 9.19397521018982, 9.197745323181152, 9.203532218933105, 9.210667848587036, 9.227073907852173, 9.337709188461304, 9.578082084655762, 9.585747480392456, 9.597790241241455, 9.617431640625, 9.632620334625244, 9.810993671417236, 9.877172708511353, 9.88805890083313, 9.996833324432373, 9.99963903427124, 10.023416757583618, 10.114044427871704, 10.231090068817139, 10.24421739578247, 10.362589120864868, 10.403590440750122, 10.422143459320068, 10.447498083114624, 10.480167865753174, 10.608006477355957, 10.632948160171509, 10.858672380447388, 10.987942695617676, 11.048926830291748, 11.347913026809692, 11.37775707244873, 11.444365978240967, 11.69433879852295, 11.744017601013184, 12.248009443283081, 13.11788821220398, 13.308318376541138, 14.244614601135254, 14.375199556350708, 14.92581033706665, 14.961844444274902, 15.135932922363281, 15.205636262893677, 15.696724891662598, 15.811850309371948, 16.172821521759033, 16.418516874313354, 16.773420095443726, 17.172746181488037, 17.244367361068726, 17.80459427833557, 17.86487889289856, 18.06466245651245, 18.148764610290527, 18.375925064086914, 18.796053647994995, 18.973535299301147, 20.94737958908081, 21.865970611572266, 22.46315050125122, 24.563895225524902, 25.004279851913452, 25.689601182937622, 25.968258142471313, 27.090924501419067, 30.050814151763916, 31.317362785339355, 49.766932249069214, 124.24178981781006]

GOOD = ['https://friendzone1.site', 'https://zigza.xyz', 'https://kittyverse.cyou', 'https://vevivo.art', 'https://vilenarios.com', 'https://aralper.shop', 'https://mz2gw.site', 'https://alloranetwork.site', 'https://nguyentinhtan.store', 'https://rilborns.xyz', 'https://greenvvv.site', 'https://longle.store', 'https://arns-gateway.com', 'https://cyanalp.store', 'https://abracata.xyz', 'https://vevivoofficial.xyz', 'https://boramir.xyz', 'https://saffronnest.site', 'https://humbleman.store', 'https://ar.randao.net', 'https://perma.online', 'https://arweave.developerdao.com', 'https://permagate.io', 'https://claminala.xyz', 'https://plumvillage.store', 'https://ar.anyone.tech', 'https://mindfull.space', 'https://lowster.site', 'https://permanodes.store', 'https://peacepixel.space', 'https://behumble.space', 'https://landoffire.store', 'https://minimoodeng.store', 'https://tpgoose.ccwu.cc', 'https://tanssi.site', 'https://regareta.xyz', 'https://moodengcute.site', 'https://kingoffireland.store', 'https://ario-maimy1.site', 'https://zyntrico.shop', 'https://khacasablanca.top', 'https://venturals.xyz', 'https://campnodesa.xyz', 'https://adaconna.top', 'https://frostor.xyz', 'https://rabbitholeshot.ccwu.cc', 'https://subspacera.xyz', 'https://kohtao.space', 'https://cagolas.xyz', 'https://arandar.online', 'https://dex12345.xyz', 'https://morue.site', 'https://cuongche-lol.store', 'https://morue.xyz', 'https://anchorfocus.space', 'https://birinci.space', 'https://starseedman.space', 'https://ar-io-gateway2.node.mulosbron.xyz', 'https://burabi.xyz', 'https://trangtien.space', 'https://nodeario.xyz', 'https://depzai.store', 'https://rubycom.online', 'https://oshvank.site', 'https://lienhoa.store', 'https://desertag.xyz', 'https://turbo-gateway.com', 'https://bluebirds.online', 'https://petalgear.online', 'https://superstone.site', 'https://kingsharald.online', 'https://onr111.space', 'https://dillnetwork.site', 'https://flechemano4.xyz', 'https://dieutiet.store', 'https://bettersafethansorry.ddns.wtf', 'https://openar.dev', 'https://ariogw.bar', 'https://mssnodes.xyz', 'https://selfrespect.store', 'https://ucuncu.store', 'https://ktten.site', 'https://haicoder.site', 'https://gauto.space', 'https://elephantsmall.store', 'https://ar7.oohgroup.vn', 'https://ardrive.net', 'https://tomania.xyz', 'https://hongmai-ao.store', 'https://lemonados.xyz', 'https://vault77.online', 'https://mipenode.pro', 'https://onc33.online', 'https://flechemano.store', 'https://hupdam.store', 'https://tphue.store', 'https://lidovault.site', 'https://flechemano5.xyz', 'https://abidik.store', 'https://6.ario.p10node.onl', 'https://xuankhai.site', 'https://cyberhill.site', 'https://elephantbig.store', 'https://algoula.xyz', 'https://hamachien.store', 'https://0.ario.p10node.onl', 'https://coshiftera.xyz', 'https://neverfapagain.space', 'https://figmentala.xyz', 'https://mymission.space', 'https://ar.skykartal.online', 'https://financefreedom.store', 'https://exnihilio.dnshome.de', 'https://pixel999.space', 'https://practicersa.xyz', 'https://5irechain.site', 'https://funday520.ccwu.cc', 'https://maplesyrup-ario.my.id', 'https://ariospeedwagon.com', 'https://ariosunucu.online', 'https://mintmoodeng.store', 'https://ar.innostack.xyz', 'https://velutan.xyz', 'https://kuaimango.space', 'https://gianai.store', 'https://fromartoao.store', 'https://ario3.aoar.io.vn', 'https://liglow.com', 'https://dezntal.xyz', 'https://demodria.xyz', 'https://withs1.store', 'https://dakher.xyz', 'https://baliner.xyz', 'https://ariogateways.space', 'https://quanho.site', 'https://ario3.arweave.io.vn', 'https://clicknimbus.shop', 'https://chaose.site', 'https://vevivofficial.store', 'https://diafora.cloud', 'https://tainaliya.xyz', 'https://wealthfinance.space', 'https://06.arweave.io.vn', 'https://ario.ario.io.vn', 'https://khang.pro', 'https://ahmkahvalidator.online', 'https://gotchas.site', 'https://ado.0x0.io.vn', 'https://jyqx75.shop', 'https://thd.io.vn', 'https://05.arweave.io.vn', 'https://ario7.aoar.io.vn', 'https://lamsachmay.store', 'https://aiagentstech.site', 'https://gizrd.store', 'https://makeal.site', 'https://complianceec.store', 'https://save.arweave.io.vn', 'https://best-slide.store', 'https://01.aoar.io.vn', 'https://kittyverse.cfd', 'https://hiddengerm.space', 'https://mameozi.store', 'https://noneq.store', 'https://gatewaypie.com', 'https://trongdo.store', 'https://ario.aoar.io.vn', 'https://ario6.aoar.io.vn', 'https://nauto.store', 'https://leapsona.xyz', 'https://4.ario.io.vn', 'https://calipsera.xyz', 'https://heminetwork.site', 'https://ainode.aoar.io.vn', 'https://webthree.site', 'https://4.ario.arweave.io.vn', 'https://nerelis.xyz', 'https://bestenemy.site', 'https://thuhuong.io.vn', 'https://ario.0x0.io.vn', 'https://naid.space', 'https://ario2.arweave.io.vn', 'https://retrogena.xyz', 'https://vfrr.io.vn', 'https://realknowledge.space', 'https://ario5.aoar.io.vn', 'https://2.0x0.io.vn', 'https://ado01.0x0.io.vn', 'https://bepatient.space', 'https://53hlm.site', 'https://ckiiem.site', 'https://stakeario.site', 'https://05.aoar.io.vn', 'https://ario.ionode.top', 'https://ario.io.vn', 'https://nhunhubs.io.vn', 'https://greatjobdone.store', 'https://02.aoar.io.vn', 'https://4.ario.0x0.io.vn', 'https://chezss.store', 'https://eyezm.space', 'https://4.ario.thd.io.vn', 'https://hue75.space', 'https://ultrasoon.site', 'https://ario8.aoar.io.vn', 'https://2.ario.io.vn', 'https://ar-io-gateway.node.mulosbron.xyz', 'https://despacito.site', 'https://nobodycare.space', 'https://aothecomputer.site', 'https://vmani.store', 'https://4.ario.ario.io.vn', 'https://luckyguy.store', 'https://buythedip.store', 'https://tttcquocte.space', 'https://llearr.store', 'https://recoverario.site', 'https://grafananode.store', 'https://ar-io.dev', 'https://tuoitho.shop', 'https://ario.resolve.bar', 'https://ppario.io.vn', 'https://otcdeal.store', 'https://only1chance.site', 'https://exploreman.store', 'https://samedilong.store', 'https://nuisong.store', 'https://lalabb.space', 'https://kellakk.space', 'https://safeario.site', 'https://wokeup.space', 'https://banhve.space', 'https://tekunode.store', 'https://09tha.store', 'https://ario4.0x0.io.vn', 'https://verysoon.site', 'https://ario2.aoar.io.vn', 'https://goldenvisa.site', 'https://nethermindnode.store', 'https://tothemar.space', 'https://wenlistingsir.store', 'https://mintnho.store', 'https://staytuned.site', 'https://dynars.store', 'https://permissionless.space', 'https://ario4.aoar.io.vn', 'https://compcp.space', 'https://2.aoar.io.vn', 'https://ario4.thd.io.vn', 'https://baoquoc1998.site', 'https://ar.tinnguyen.xyz', 'https://djeverasa.xyz', 'https://ario5.thd.io.vn', 'https://uytin.store', 'https://loveario.site', 'https://lalabbs.xyz', 'https://llearr.xyz', 'https://web3man.space', 'https://solostaker.store', 'https://3.ario.io.vn', 'https://4.ario.ctytanviet.vn', 'https://ario3.0x0.io.vn', 'https://seikooz.xyz', 'https://ario-tothemoon1.store', 'https://1ngaymoi.io.vn', 'https://03.aoar.io.vn', 'https://3.0x0.io.vn', 'https://ario5.0x0.io.vn', 'https://01.arweave.io.vn', 'https://lodiix.io.vn', 'https://phatriet.site', 'https://ckbi.space', 'https://thuhuong.space', 'https://wensoon.site', 'https://saveario.site', 'https://derad.network', 'https://samedilong.io.vn', 'https://04.arweave.io.vn', 'https://0x0.io.vn', 'https://4.ario.aoar.io.vn', 'https://highestmind.store', 'https://letitbe.space', 'https://cuongcc.io.vn', 'https://ario3.thd.io.vn', 'https://aoar.io.vn', 'https://behero.space', 'https://1.ario.p10node.onl', 'https://8.ario.p10node.onl', 'https://ar6.noddex.com', 'https://ario.ctytanviet.vn', 'https://ar1.innostack.xyz', 'https://luciziz.site', 'https://2.ario.p10node.onl', 'https://ivandivandelen.site', 'https://ar7.innostack.xyz', 'https://jembutkucing.online', 'https://ario.thd.io.vn', 'https://nieaka.space', 'https://ario2.ario.io.vn', 'https://glassmm.store', 'https://ario10.aoar.io.vn', 'https://zmaokhe.store', 'https://chillpoz.space', 'https://ario9.aoar.io.vn', 'https://treex.online', 'https://gaunho.space', 'https://thabu.store', 'https://truongha.site', 'https://ario-1usd.store', 'https://lazzyp.store', 'https://ario2.thd.io.vn', 'https://bravetz.store', 'https://arweave.io.vn', 'https://bimmup.store', 'https://06.aoar.io.vn', 'https://2year-pump1.site']

BAD = ['https://reeta.online', 'https://ken1.site', 'https://khanhwizardpa.store', 'https://ikinci.store', 'https://enyaselessar.xyz', 'https://flechemano.space', 'https://bynorena.xyz', 'https://miraynodes.website', 'https://bulltega.xyz', 'https://gentlepenguin.online', 'https://crystalbell.online', 'https://navs.store', 'https://polinder.xyz', 'https://crocan.store', 'https://mintervil.xyz', 'https://yieldmon.xyz', 'https://stainal.xyz', 'https://stroyen.xyz', 'https://velanor.xyz', 'https://bushidows.xyz', 'https://isgreat.xyz', 'https://thuanannew1.store', 'https://loton1.store', 'https://ladantel.xyz', 'https://vidual.xyz', 'https://radors.xyz', 'https://arweave.services.kyve.network', 'https://arweave.ar', 'https://ar.owlstake.com', 'https://rikimaru111.site', 'https://ar.perplex.finance', 'https://mrciga.com', 'https://hazmaniaxbt.online', 'https://pi314.xyz', 'https://cavgas.xyz', 'https://dtractusrpca.xyz', 'https://crbaa.xyz', 'https://hlldrk.shop', 'https://canduesed.me', 'https://yolgezer55.xyz', 'https://tefera.xyz', 'https://euraquilo.xyz', 'https://krayir.xyz', 'https://mustafakaya.xyz', 'https://beyzako.xyz', 'https://htonka.xyz', 'https://arceina.store', 'https://baristestnet.xyz', 'https://darksunrayz.store', 'https://babayagax.online', 'https://rodruquez.online', 'https://itsyalcin.xyz', 'https://alpt.autos', 'https://ruangnode.xyz', 'https://khaldrogo.site', 'https://karakartal.store', 'https://svgtmrgl.xyz', 'https://kabaoglu.xyz', 'https://boramir.store', 'https://iblis.store', 'https://sunkripto.site', 'https://mehteroglu.store', 'https://barburan.site', 'https://auquis.online', 'https://chocon.store', 'https://salakk.online', 'https://mustafakara.space', 'https://linaril.xyz', 'https://leechshop.com', 'https://kagithavlu.store', 'https://rtmpsunucu.online', 'https://ar.taskopru.xyz', 'https://terminatormbd.com', 'https://koltigin.xyz', 'https://0xyvz.xyz', 'https://kahvenodes.online', 'https://yukovskibot.com', 'https://0xsav.xyz', 'https://ar.riceinbucket.com', 'https://yusufaytn.xyz', 'https://2save.xyz', 'https://rollape.com.tr', 'https://koniq.xyz', 'https://ainodes.xyz', 'https://arweave.auduge.com', 'https://ar.0xskyeagle.com', 'https://ar.ionode.online', 'https://wenairdropsir.store', 'https://ar.bearnode.xyz', 'https://fisneci.com', 'https://ar-node.megastake.org', 'https://astrocosmos.website', 'https://ar.secret-network.xyz', 'https://adora0x0.xyz', 'https://ar-testnet.p10node.com', 'https://ar.satoshispalace.casino', 'https://imtran.site', 'https://katsumii.xyz', 'https://nodebeta.site', 'https://blockchain-ario.store', 'https://ario.dasamuka.xyz', 'https://kt10vip.online', 'https://thanhapple.store', 'https://meocon.store', 'https://commissar.xyz', 'https://gisela-arg.xyz', 'https://sadas655.xyz', 'https://kenyaligeralt.xyz', 'https://ruyisu.net', 'https://0xmonyaaa.xyz', 'https://zirhelp.lol', 'https://gmajorscale.xyz', 'https://g8way.0rbit.co', 'https://misatoshi.pics', 'https://clyapp.xyz', 'https://dilsinay.online', 'https://secondtornado.xyz', 'https://mpsnode.online', 'https://gateway.getweave.org', 'https://comrat32.xyz', 'https://konobbeybackend.online', 'https://nodecoyote.xyz', 'https://sabrig1480.xyz', 'https://kingsharald.xyz', 'https://blockchainzk.website', 'https://vevivo.xyz', 'https://software0x.website', 'https://dasamuka.cloud', 'https://shapezero.xyz', 'https://bootstrap.lol', 'https://canduesed.xyz', 'https://nodeinvite.xyz', 'https://lethuan.xyz', 'https://bburan.xyz', 'https://velaryon.xyz', 'https://anch0r.com', 'https://thecoldblooded.online', 'https://moruehoca.online', 'https://cahil.store', 'https://dnsarz.wtf', 'https://rerererararags.store', 'https://validatorario.xyz', 'https://sefaaa.online', 'https://ahmkah.online', 'https://thecoldblooded.store', 'https://diafora.tech', 'https://berso.store', 'https://moruehoca.store', 'https://dilsinay2814.online', 'https://mutu.lol', 'https://cetinsefa.online', 'https://validatario.xyz', 'https://aantop.xyz', 'https://enesss.online', 'https://graski.xyz', 'https://wanr.top', 'https://arnode.cfd', 'https://aslanas01.xyz', 'https://shadow39.online', 'https://jaxtothehell.xyz', 'https://parkdongfeng.store', 'https://r4dn.tech', 'https://darthlyrex.xyz', 'https://acanpolat.xyz', 'https://arnode.xyz', 'https://prowsemre.online', 'https://nodevietnam.com', 'https://sygnblock.xyz', 'https://bodhiirozt.xyz', 'https://coinhunterstr.site', 'https://techvenience.net', 'https://apayro.xyz', 'https://anaraydinli.xyz', 'https://mrcetin03.store', 'https://cakonline.xyz', 'https://budavlebac.online', 'https://loriscant.site', 'https://0xsaitomo.xyz', 'https://neuweltgeld.xyz', 'https://arlogmein.xyz', 'https://arendor.xyz', 'https://ariozerowave.my.id', 'https://webraizo.online', 'https://xiaocloud.site', 'https://thekayz.xyz', 'https://captsuck.xyz', 'https://minhbear.xyz', 'https://Phuc.top', 'https://ibrahimdirik.xyz', 'https://sedat07.xyz', 'https://herculesnode.shop', 'https://cayu7pa.xyz', 'https://mahcubyan.xyz', 'https://0xknowledge.store', 'https://testnetnodes.xyz', 'https://gurkanceltin.online', 'https://stevnode.site', 'https://ongtrong.xyz', 'https://kecil.tech', 'https://myphamalma.com', 'https://lanchiaw.xyz', 'https://getblock.store', 'https://emireray.shop', 'https://lobosqlinc.site', 'https://polkasub.site', 'https://shapezero.site', 'https://ario.stake.nexus', 'https://digitclone.online', 'https://lostgame.online', 'https://mutu.pro', 'https://ar-dreamnode.xyz', 'https://diafora.site', 'https://aleko0o.store', 'https://vn-sti.top', 'https://flexibleee.xyz', 'https://soulbreaker.xyz', 'https://parafmax.site', 'https://omersukrubektas.online', 'https://node69.site', 'https://mertorakk.xyz', 'https://kanan1.shop', 'https://bsckapp.store', 'https://arweave.validator.wiki', 'https://arbr.pro', 'https://kiem-tran.tech', 'https://dnsarz.site', 'https://arweaveblock.com', 'https://didzcover.world', 'https://bambik.online', 'https://deknow.top', 'https://ar.alwaysbedream.dev', 'https://lobibo.online', 'https://teoteovivi.store', 'https://herculesnode.online', 'https://codehodl.xyz', 'https://kittyverse.skin', 'https://aothecomputer.xyz', 'https://ario-testnet.us.nodefleet.org', 'https://exodusdiablo.xyz', 'https://dwentz.site', 'https://iogate.uk', 'https://stonkson.xyz', 'https://iogate.co.uk', 'https://aksamlan.xyz', 'https://vrising.site', 'https://ozzcanx.xyz', 'https://flashwayne.online', 'https://utkububa.xyz', 'https://apeweave.com', 'https://nodebiz.site', 'https://arioarioario.online', 'https://ahmkahvalidator.xyz', 'https://nodehub.site', 'https://ar.ilaybilge.xyz', 'https://redwhiteconnect.xyz', 'https://software0x.space', 'https://snafyr.xyz', 'https://anti-mage01.store', 'https://ioar.xyz', 'https://flechemano.com', 'https://spectre01.site', 'https://alexxis.store', 'https://maclaurino.xyz', 'https://bicem.xyz', 'https://torku.xyz', 'https://ar.kiranli.xyz', 'https://vnnode.top', 'https://sarlos.site', 'https://frogzz.xyz', 'https://sakultarollapp.site', 'https://nodezeta.site', 'https://bootstrap.icu', 'https://slatrokh.xyz', 'https://blessingway.xyz', 'https://alicans.online', 'https://practicers.xyz', 'https://senzura.xyz', 'https://campnode.xyz', 'https://elessardarken.xyz', 'https://treexyz.site', 'https://doflamingo.xyz', 'https://recepgocmen.xyz', 'https://nodetitan.site', 'https://sametyuksel.xyz', 'https://hexamz.tech', 'https://coshift.xyz', 'https://mrheracles.online', 'https://vikanren.buzz', 'https://vevivofficial.xyz', 'https://ariogateway.online', 'https://arnode.site', 'https://weaversnodes.info', 'https://chaintech.site', 'https://zerolight.online', 'https://adn79.pro', 'https://nodetester.com', 'https://regaret.xyz', 'https://kazazel.xyz', 'https://0xkullanici.online', 'https://erenynk.xyz', 'https://nodepepe.site', 'https://ar.tomris.xyz', 'https://ar.phuongvusolution.com', 'https://mulosbron.xyz', 'https://gatewaykeeper.net', 'https://zekkava.space', 'https://kunacan.xyz', 'https://grenimo.click', 'https://nodechecker.xyz', 'https://yakupgs.online', 'https://ar-arweave.xyz', 'https://nodevip.site', 'https://love4src.com', 'https://eaddaa.website', 'https://sowyer.xyz', 'https://ivandivandelen.online', 'https://stajertestnetci.site', 'https://pentav.site', 'https://ahnetd.online', 'https://zionalc.online', 'https://cyanalp.cfd', 'https://stilucky.top', 'https://ykpbb.xyz', 'https://mdbmesutmdb.shop', 'https://erenkurt.site', 'https://murod.xyz', 'https://aralper.xyz', 'https://kingsharaldoperator.xyz', 'https://merttemizer.xyz', 'https://tekin86.online', 'https://ademtor.xyz', 'https://kyotoorbust.site', 'https://cmdexe.xyz', 'https://sooneraydin.xyz', 'https://avempace.xyz', 'https://ario.oceanprotocol.com', 'https://stevnode.space', 'https://spacemarko.xyz', 'https://ariobrain.xyz', 'https://xacminh.store', 'https://hupso.store', 'https://kurabi.space', 'https://castilan.site', 'https://rockndefi.xyz', 'https://aoweave.tech', 'https://thique1.site', 'https://bobinstein.com', 'https://imontral.xyz', 'https://decentralizeguys.store', 'https://11.ario.p10node.onl', 'https://mydeepstate.space', 'https://denual.xyz', 'https://meditationlove.space', 'https://cayvl.store', 'https://dymwizard.space', 'https://giantmoodeng.site', 'https://arweave.fllstck.dev', 'https://ronganminh.site', 'https://owlorangejuice.bar', 'https://5.ario.p10node.onl', 'https://rufetnaliyev.store', 'https://tekin86.site', 'https://siyantest.shop', 'https://imyadomena.online', 'https://txhoang.site', 'https://hoanminh.site', 'https://renekta.xyz', 'https://kollmz.site', 'https://boy75.store', 'https://phuxuan1.site', 'https://khuachina.site', 'https://arweave.ddns.berlin', 'https://zerosettle.xyz', 'https://decaprios.xyz', 'https://ario.arweave.io.vn', 'https://omies.space', 'https://junnew.site', 'https://ario.koltigin.xyz', 'https://huenews.space', 'https://communitynode.dnshome.eu', 'https://llct.space', 'https://nguyenthi.site', 'https://vf6plus.site', 'https://ar.qavurdagli.online', 'https://ar8.innostack.xyz', 'https://ar2.noddex.com', 'https://hupsoapsoap.store', 'https://ar9.innostack.xyz', 'https://decentralizelocation.space', 'https://permaweb.cfd', 'https://arnexus.cfd', 'https://ar6.oohgroup.vn', 'https://ar7.noddex.com', 'https://ar2.innostack.xyz', 'https://eatcleanwater.space', 'https://ahmetcan.store', 'https://ilgazsoy.store', 'https://dyorfinance.site', 'https://ar8.noddex.com', 'https://dumdump.space', 'https://ar1.oohgroup.vn', 'https://trinhsatkhonggianmang.space', 'https://mintlamay.site', 'https://khoaito.site', 'https://kakalot.online', 'https://seeyouselfboy.store', 'https://dimori.space', 'https://trinhsatdaitai.space', 'https://voinetwork.site', 'https://altseason.space', 'https://dependenceboys.site', 'https://retardo.site', 'https://paxjudeica.space', 'https://cyberfly.store', 'https://noblesilence.site', 'https://mimboku.space', 'https://kgenesys.space', 'https://tamduong.site', 'https://cashwaterflow.space', 'https://ar6.innostack.xyz', 'https://ar12.innostack.xyz', 'https://thanhapple.site', 'https://hinhsu-no1.site', 'https://arweave.net', 'https://ar3.noddex.com', 'https://ar5.noddex.com', 'https://ar1.stilucky.xyz', 'https://ar2.stilucky.xyz', 'https://ar3.stilucky.xyz', 'https://ar4.stilucky.xyz', 'https://ar10.stilucky.xyz', 'https://ar11.stilucky.xyz', 'https://ar16.stilucky.xyz', 'https://g1.vnar.xyz', 'https://ar18.stilucky.xyz', 'https://ar19.stilucky.xyz', 'https://ar17.stilucky.xyz', 'https://g2.vnar.xyz', 'https://g4.vnar.xyz', 'https://g5.vnar.xyz', 'https://g3.vnar.xyz', 'https://g7.vnar.xyz', 'https://g8.vnar.xyz', 'https://g9.vnar.xyz', 'https://g14.vnar.xyz', 'https://g10.vnar.xyz', 'https://g6.vnar.xyz', 'https://g17.vnar.xyz', 'https://g15.vnar.xyz', 'https://g20.vnar.xyz', 'https://g16.vnar.xyz', 'https://g18.vnar.xyz', 'https://g19.vnar.xyz', 'https://ar20.stilucky.xyz', 'https://fudcrypto.space', 'https://arweave.tokyo', 'https://g21.vnar.xyz', 'https://ar21.stilucky.xyz', 'https://g22.vnar.xyz', 'https://ar23.stilucky.xyz', 'https://ar22.stilucky.xyz', 'https://ar24.stilucky.xyz', 'https://g24.vnar.xyz', 'https://g23.vnar.xyz', 'https://g12.vnar.xyz', 'https://ar5.stilucky.xyz', 'https://ar6.stilucky.xyz', 'https://ar.ominas.ovh', 'https://ar2.ominas.ovh', 'https://alicans.site', 'https://arweave.zelf.world', 'https://ar8.oohgroup.vn', 'https://ar4.noddex.com', 'https://ar2.oohgroup.vn', 'https://liluandinhcao.store', 'https://semedo.site', 'https://umutdogan.space', 'https://flechemano.online', 'https://ario-gateway.nethermind.dev', 'https://ario.bayur.net', 'https://onetwothreemoving.space', 'https://g11.vnar.xyz', 'https://1mblock.space', 'https://ar5.oohgroup.vn', 'https://g13.vnar.xyz', 'https://ar12.stilucky.xyz', 'https://ar15.stilucky.xyz', 'https://ar8.stilucky.xyz', 'https://ar14.stilucky.xyz', 'https://brownmoodeng.store', 'https://ar13.stilucky.xyz', 'https://ar9.stilucky.xyz', 'https://araoai.com', 'https://ong3.xyz', 'https://sulapan.com', 'https://kt10.site', 'https://germancoin.space', 'https://donkichot.space', 'https://nguyenhoang1.site', 'https://sultanfateh.store', 'https://bienchecung.store', 'https://emilywalker.space', 'https://beyondstars.store', 'https://shreksson.store', 'https://gubidik.store', 'https://perma-swap.space', 'https://donchon.store', 'https://ar5.innostack.xyz', 'https://drrufana.online', 'https://arlink.xyz', 'https://loriscant.space', 'https://10.ario.p10node.onl', 'https://greenxanh.xyz', 'https://youmust.store', 'https://dangkhoi-ken.store', 'https://tefera.site', 'https://ario-lol.store', 'https://dieulenh.site', 'https://geralt.space', 'https://ar15.innostack.xyz', 'https://pentav.cloud', 'https://aoshield.online', 'https://fromchinatoeu.store', 'https://12.ario.p10node.onl', 'https://7.ario.p10node.onl', 'https://perma-web.store', 'https://altugario.space', 'https://phugiavip.store', 'https://ar4.innostack.xyz', 'https://sieucapchinhtri.store', 'https://daemongate.io', 'https://ar11.innostack.xyz', 'https://ar9.noddex.com', 'https://ar13.innostack.xyz', 'https://hamanau.store', 'https://ar3.innostack.xyz', 'https://ar10.innostack.xyz', 'https://3.ario.p10node.onl', 'https://zerolighta.xyz', 'https://4.ario.p10node.onl', 'https://ar9.oohgroup.vn', 'https://ar1.noddex.com', 'https://arioex.xyz', 'https://ar11.oohgroup.vn', 'https://ar10.oohgroup.vn', 'https://smndfir.space', 'https://ar14.innostack.xyz', 'https://gmvietnam.site', 'https://02.arweave.io.vn', 'https://2.arweave.io.vn', 'https://ar4.oohgroup.vn', 'https://ar.vnnode.com', 'https://04.aoar.io.vn', 'https://mooncoffee.store', 'https://penmr.io.vn', 'https://ado02.0x0.io.vn', 'https://dontworrybro.space', 'https://juneo.site', 'https://trump-ario.site', 'https://03.arweave.io.vn', 'https://amelaz.space', 'https://bestdepin.site', 'https://khoday.store', 'https://protectario.site', 'https://ariohome.space', 'https://ario-check.site', 'https://ar3.oohgroup.vn', 'https://ario2.0x0.io.vn', 'https://ar.oohgroup.vn', 'https://villina.store', 'https://freakyman.site', 'https://certifp.store', 'https://byd-dream.site']
