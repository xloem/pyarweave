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

TIMES = [2.693441390991211, 2.7108185291290283, 2.7167720794677734, 3.4849376678466797, 3.6130361557006836, 3.6511285305023193, 3.6949620246887207, 3.728123664855957, 3.7811126708984375, 3.824829578399658, 3.8419294357299805, 3.8521690368652344, 3.877485513687134, 3.8788249492645264, 3.966228723526001, 3.967013120651245, 3.978229522705078, 3.9801321029663086, 3.9938366413116455, 4.0017454624176025, 4.014266014099121, 4.02631402015686, 4.028151035308838, 4.038244962692261, 4.0923731327056885, 4.100769281387329, 4.169280767440796, 4.179730653762817, 4.184627294540405, 4.189831972122192, 4.191560983657837, 4.2230916023254395, 4.2330710887908936, 4.2385101318359375, 4.238558053970337, 4.2412049770355225, 4.247753381729126, 4.255805492401123, 4.257460117340088, 4.265338182449341, 4.275682210922241, 4.305506944656372, 4.33018946647644, 4.333853006362915, 4.341311931610107, 4.360577344894409, 4.388691425323486, 4.391207218170166, 4.4041008949279785, 4.469278812408447, 4.481611251831055, 4.498852729797363, 4.5299928188323975, 4.531278610229492, 4.531428098678589, 4.543302774429321, 4.5546040534973145, 4.554676294326782, 4.555118083953857, 4.564855098724365, 4.571160554885864, 4.581075668334961, 4.586404323577881, 4.603058576583862, 4.636073112487793, 4.660714626312256, 4.66148567199707, 4.693739652633667, 4.695012331008911, 4.697250843048096, 4.714118003845215, 4.731495141983032, 4.7499964237213135, 4.758583307266235, 4.759244203567505, 4.7759833335876465, 4.776648759841919, 4.782609462738037, 4.788109540939331, 4.78939414024353, 4.826946020126343, 4.837226390838623, 4.853341579437256, 4.867868185043335, 4.890305757522583, 4.933361053466797, 4.966486930847168, 4.976658582687378, 5.003702640533447, 5.0051774978637695, 5.0113794803619385, 5.078526735305786, 5.080474853515625, 5.098816394805908, 5.09959602355957, 5.112112998962402, 5.170633792877197, 5.187864303588867, 5.219658613204956, 5.241731643676758, 5.248769283294678, 5.262446403503418, 5.264316082000732, 5.301009893417358, 5.310403823852539, 5.320668458938599, 5.342353820800781, 5.354867219924927, 5.360491991043091, 5.454613447189331, 5.459129333496094, 5.467466831207275, 5.473878622055054, 5.474236249923706, 5.475758790969849, 5.521748065948486, 5.529170513153076, 5.596879720687866, 5.617247581481934, 5.619473457336426, 5.625310897827148, 5.625887155532837, 5.628730297088623, 5.663135528564453, 5.730574369430542, 5.787350177764893, 5.792638540267944, 5.8656816482543945, 5.8691651821136475, 5.929339647293091, 5.9549407958984375, 5.994793653488159, 6.141479730606079, 6.218382358551025, 6.230032205581665, 6.275314569473267, 6.2801690101623535, 6.293871641159058, 6.321039915084839, 6.3215556144714355, 6.329873323440552, 6.3308141231536865, 6.348694801330566, 6.354393720626831, 6.411304712295532, 6.441998720169067, 6.477820158004761, 6.530858278274536, 6.54002833366394, 6.5440497398376465, 6.54880690574646, 6.553055286407471, 6.597774505615234, 6.6266257762908936, 6.650355577468872, 6.651132106781006, 6.672045946121216, 6.688286542892456, 6.703662395477295, 6.789557218551636, 6.814554214477539, 6.828610420227051, 6.872189998626709, 6.917172908782959, 6.917743921279907, 6.949632167816162, 6.960842609405518, 7.0061070919036865, 7.023058891296387, 7.039686441421509, 7.064289093017578, 7.098601818084717, 7.12673282623291, 7.155681133270264, 7.1617209911346436, 7.205250024795532, 7.2460784912109375, 7.32649040222168, 7.35053014755249, 7.379989147186279, 7.3837103843688965, 7.3855249881744385, 7.455615997314453, 7.496636629104614, 7.514164209365845, 7.5458903312683105, 7.5626842975616455, 7.5997154712677, 7.616692066192627, 7.618647336959839, 7.632731914520264, 7.688526630401611, 7.69334864616394, 7.6941328048706055, 7.749836444854736, 7.811440467834473, 7.820390462875366, 7.829066753387451, 7.87159276008606, 7.921540260314941, 7.923984050750732, 7.927405834197998, 7.974043607711792, 7.982685804367065, 8.034611225128174, 8.104227781295776, 8.16650652885437, 8.201236248016357, 8.35430383682251, 8.380022048950195, 8.387163639068604, 8.43984079360962, 8.475847959518433, 8.522003650665283, 8.53123140335083, 8.588107109069824, 8.590837240219116, 8.644331216812134, 8.645947933197021, 8.702324867248535, 8.770063638687134, 8.792601108551025, 8.79685640335083, 8.799720525741577, 8.802539348602295, 8.970503330230713, 8.97289752960205, 9.000183343887329, 9.061339139938354, 9.070071935653687, 9.074977397918701, 9.113466739654541, 9.128595113754272, 9.210091590881348, 9.21656346321106, 9.317836999893188, 9.34761929512024, 9.402159214019775, 9.40834665298462, 9.411264657974243, 9.476046323776245, 9.53386116027832, 9.601665019989014, 9.615417957305908, 9.61542296409607, 9.620545148849487, 9.679279088973999, 9.694175481796265, 9.701741933822632, 9.816374778747559, 9.819379329681396, 9.824979543685913, 9.829582691192627, 9.980512142181396, 10.013808012008667, 10.015568256378174, 10.033396005630493, 10.112074613571167, 10.137407302856445, 10.148432731628418, 10.226440191268921, 10.233641147613525, 10.41214632987976, 10.431461095809937, 10.433858394622803, 10.472326278686523, 10.499152421951294, 10.502378702163696, 10.50638723373413, 10.515653610229492, 10.518483877182007, 10.533799171447754, 10.590117692947388, 10.599544763565063, 10.63273024559021, 10.749908208847046, 10.808499574661255, 10.848896741867065, 11.044458389282227, 11.061854124069214, 11.128898620605469, 11.168329000473022, 11.21064829826355, 11.211793661117554, 11.272619485855103, 11.442567110061646, 11.65638017654419, 11.658822774887085, 11.898347854614258, 11.900598287582397, 12.11200761795044, 12.117895603179932, 12.250549793243408, 13.002085208892822, 13.042774438858032, 13.712966680526733, 14.113524198532104, 14.121646404266357, 15.397525310516357, 15.643414974212646, 16.24587893486023, 16.584136962890625, 17.16342854499817, 17.199129104614258, 17.2129545211792, 17.417279958724976, 17.457144737243652, 17.717013359069824, 17.80560541152954, 18.94957947731018, 19.21043038368225, 20.052289247512817, 20.4302020072937, 20.533935070037842, 20.716665267944336, 21.480168342590332, 22.847691774368286, 22.927146911621094, 23.30065631866455, 24.208009481430054, 24.3082857131958, 24.349764108657837, 24.776810884475708, 25.11055016517639, 29.223108053207397, 30.71631407737732, 31.2331223487854, 32.35907435417175, 35.412407636642456, 35.90600943565369, 47.93472957611084]

GOOD = ['https://perma.online', 'https://friendzone1.site', 'https://gatewaypie.com', 'https://ariogw.bar', 'https://daemongate.io', 'https://vilenarios.com', 'https://vevivoofficial.xyz', 'https://lemonados.xyz', 'https://ar.anyone.tech', 'https://moodengcute.site', 'https://peacepixel.space', 'https://oshvank.site', 'https://ar-io-gateway2.node.mulosbron.xyz', 'https://nguyentinhtan.store', 'https://dex12345.xyz', 'https://onr111.space', 'https://onc33.online', 'https://gauto.space', 'https://behumble.space', 'https://tomania.xyz', 'https://ardrive.net', 'https://longle.store', 'https://ar11.innostack.xyz', 'https://neverfapagain.space', 'https://turbo-gateway.com', 'https://vault77.online', 'https://minimoodeng.store', 'https://arandar.online', 'https://adaconna.top', 'https://saffronnest.site', 'https://alloranetwork.site', 'https://kingsharald.online', 'https://mintmoodeng.store', 'https://rilborns.xyz', 'https://landoffire.store', 'https://starseedman.space', 'https://mymission.space', 'https://derad.network', 'https://arweave.developerdao.com', 'https://cyberhill.site', 'https://ktten.site', 'https://lienhoa.store', 'https://ario-maimy1.site', 'https://plumvillage.store', 'https://kuaimango.space', 'https://vevivo.art', 'https://permanodes.store', 'https://demodria.xyz', 'https://ahmkahvalidator.online', 'https://frostor.xyz', 'https://ar.randao.net', 'https://morue.xyz', 'https://ar9.noddex.com', 'https://arns-gateway.com', 'https://bluebirds.online', 'https://flechemano.store', 'https://velutan.xyz', 'https://khacasablanca.top', 'https://subspacera.xyz', 'https://humbleman.store', 'https://jyqx75.shop', 'https://hongmai-ao.store', 'https://greenvvv.site', 'https://openar.dev', 'https://aralper.shop', 'https://rubycom.online', 'https://mindfull.space', 'https://petalgear.online', 'https://practicersa.xyz', 'https://nodeario.xyz', 'https://ar13.innostack.xyz', 'https://bettersafethansorry.ddns.wtf', 'https://clicknimbus.shop', 'https://elephantbig.store', 'https://hamanau.store', 'https://selfrespect.store', 'https://tainaliya.xyz', 'https://trangtien.space', 'https://kittyverse.cyou', 'https://ar3.innostack.xyz', 'https://regareta.xyz', 'https://dillnetwork.site', 'https://exnihilio.dnshome.de', 'https://ar10.innostack.xyz', 'https://boramir.xyz', 'https://desertag.xyz', 'https://burabi.xyz', 'https://8.ario.p10node.onl', 'https://venturals.xyz', 'https://rabbitholeshot.ccwu.cc', 'https://zigza.xyz', 'https://depzai.store', 'https://abidik.store', 'https://aiagentstech.site', 'https://haicoder.site', 'https://abracata.xyz', 'https://webthree.site', 'https://mz2gw.site', 'https://1.ario.p10node.onl', 'https://morue.site', 'https://dezntal.xyz', 'https://algoula.xyz', 'https://elephantsmall.store', 'https://3.ario.p10node.onl', 'https://ar.skykartal.online', 'https://zerolighta.xyz', 'https://gianai.store', 'https://4.ario.p10node.onl', 'https://ar1.innostack.xyz', 'https://superstone.site', 'https://ar9.oohgroup.vn', 'https://ar1.noddex.com', 'https://ario.resolve.bar', 'https://baliner.xyz', 'https://ainode.aoar.io.vn', 'https://hamachien.store', 'https://ucuncu.store', 'https://dieutiet.store', 'https://financefreedom.store', 'https://mipenode.pro', 'https://tphue.store', 'https://nerelis.xyz', 'https://figmentala.xyz', 'https://liglow.com', 'https://calipsera.xyz', 'https://best-slide.store', 'https://ariosunucu.online', 'https://arioex.xyz', 'https://hupdam.store', 'https://retrogena.xyz', 'https://ar-io.dev', 'https://ario3.aoar.io.vn', 'https://tanssi.site', 'https://kittyverse.cfd', 'https://02.aoar.io.vn', 'https://ariospeedwagon.com', 'https://ariogateways.space', 'https://ar11.oohgroup.vn', 'https://cyanalp.store', 'https://cagolas.xyz', 'https://kohtao.space', 'https://tpgoose.ccwu.cc', 'https://3.0x0.io.vn', 'https://5irechain.site', 'https://flechemano5.xyz', 'https://ario7.aoar.io.vn', 'https://trongdo.store', 'https://2.ario.io.vn', 'https://kingoffireland.store', 'https://ar10.oohgroup.vn', 'https://smndfir.space', 'https://ar-io-gateway.node.mulosbron.xyz', 'https://lamsachmay.store', 'https://ado.0x0.io.vn', 'https://complianceec.store', 'https://maplesyrup-ario.my.id', 'https://ar14.innostack.xyz', 'https://01.aoar.io.vn', 'https://gmvietnam.site', 'https://02.arweave.io.vn', 'https://funday520.ccwu.cc', 'https://0x0.io.vn', 'https://diafora.cloud', 'https://2.arweave.io.vn', 'https://highestmind.store', 'https://ario.aoar.io.vn', 'https://ario8.aoar.io.vn', 'https://vevivofficial.store', 'https://heminetwork.site', 'https://mameozi.store', 'https://3.ario.io.vn', 'https://nauto.store', 'https://ario.ionode.top', 'https://save.arweave.io.vn', 'https://leapsona.xyz', 'https://05.arweave.io.vn', 'https://luckyguy.store', 'https://06.arweave.io.vn', 'https://ar4.oohgroup.vn', 'https://gotchas.site', 'https://quanho.site', 'https://nobodycare.space', 'https://realknowledge.space', 'https://vmani.store', 'https://ar.innostack.xyz', 'https://withs1.store', 'https://dakher.xyz', 'https://lowster.site', 'https://ar.vnnode.com', 'https://ario6.aoar.io.vn', 'https://makeal.site', 'https://thuhuong.io.vn', 'https://noneq.store', 'https://04.aoar.io.vn', 'https://chaose.site', 'https://ario.thd.io.vn', 'https://mooncoffee.store', 'https://aothecomputer.site', 'https://ultrasoon.site', 'https://baoquoc1998.site', 'https://53hlm.site', 'https://ado01.0x0.io.vn', 'https://gaunho.space', 'https://ar6.noddex.com', 'https://penmr.io.vn', 'https://hue75.space', 'https://2.0x0.io.vn', 'https://4.ario.io.vn', 'https://permissionless.space', 'https://nethermindnode.store', 'https://pixel999.space', 'https://llearr.xyz', 'https://ario3.arweave.io.vn', 'https://fromartoao.store', 'https://ado02.0x0.io.vn', 'https://kellakk.space', 'https://wensoon.site', 'https://buythedip.store', 'https://ario2.ario.io.vn', 'https://saveario.site', 'https://loveario.site', 'https://mintnho.store', 'https://grafananode.store', 'https://dontworrybro.space', 'https://eyezm.space', 'https://1ngaymoi.io.vn', 'https://juneo.site', 'https://stakeario.site', 'https://compcp.space', 'https://lalabbs.xyz', 'https://recoverario.site', 'https://trump-ario.site', 'https://tuoitho.shop', 'https://web3man.space', 'https://09tha.store', 'https://banhve.space', 'https://goldenvisa.site', 'https://staytuned.site', 'https://nuisong.store', 'https://greatjobdone.store', 'https://lalabb.space', 'https://anchorfocus.space', 'https://despacito.site', 'https://thuhuong.space', 'https://llearr.store', 'https://samedilong.store', 'https://only1chance.site', 'https://permagate.io', 'https://03.arweave.io.vn', 'https://chezss.store', 'https://tekunode.store', 'https://exploreman.store', 'https://amelaz.space', 'https://lodiix.io.vn', 'https://tttcquocte.space', 'https://ario5.0x0.io.vn', 'https://ar.tinnguyen.xyz', 'https://zyntrico.shop', 'https://bestdepin.site', 'https://06.aoar.io.vn', 'https://treex.online', 'https://otcdeal.store', 'https://seikooz.xyz', 'https://tothemar.space', 'https://khoday.store', 'https://2year-pump1.site', 'https://04.arweave.io.vn', 'https://ario2.thd.io.vn', 'https://ario4.0x0.io.vn', 'https://hiddengerm.space', 'https://bepatient.space', 'https://verysoon.site', 'https://ario4.aoar.io.vn', 'https://wealthfinance.space', 'https://safeario.site', 'https://letitbe.space', 'https://nhunhubs.io.vn', 'https://protectario.site', 'https://gizrd.store', 'https://cuongcc.io.vn', 'https://bestenemy.site', 'https://jembutkucing.online', 'https://ario5.thd.io.vn', 'https://ario4.thd.io.vn', 'https://nieaka.space', 'https://ivandivandelen.site', 'https://ariohome.space', 'https://ario-check.site', 'https://thabu.store', 'https://ario9.aoar.io.vn', 'https://ario.ctytanviet.vn', 'https://wokeup.space', 'https://flechemano4.xyz', 'https://mssnodes.xyz', 'https://bravetz.store', 'https://ppario.io.vn', 'https://solostaker.store', 'https://samedilong.io.vn', 'https://wenlistingsir.store', 'https://ario5.aoar.io.vn', 'https://ario3.0x0.io.vn', 'https://vfrr.io.vn', 'https://03.aoar.io.vn', 'https://zmaokhe.store', 'https://cuongche-lol.store', 'https://naid.space', 'https://ar3.oohgroup.vn', 'https://ario2.arweave.io.vn', 'https://uytin.store', 'https://thd.io.vn', 'https://ario2.0x0.io.vn', 'https://ar.oohgroup.vn', 'https://glassmm.store', 'https://lidovault.site', 'https://arweave.io.vn', 'https://ckbi.space', 'https://ario.0x0.io.vn', 'https://bimmup.store', 'https://villina.store', 'https://2.aoar.io.vn', 'https://chillpoz.space', 'https://freakyman.site', 'https://behero.space', 'https://ario-tothemoon1.store', 'https://lazzyp.store', 'https://certifp.store', 'https://ario-1usd.store', 'https://luciziz.site', 'https://01.arweave.io.vn', 'https://byd-dream.site', 'https://dynars.store']

BAD = ['https://reeta.online', 'https://ken1.site', 'https://khanhwizardpa.store', 'https://ikinci.store', 'https://enyaselessar.xyz', 'https://flechemano.space', 'https://bynorena.xyz', 'https://miraynodes.website', 'https://bulltega.xyz', 'https://gentlepenguin.online', 'https://crystalbell.online', 'https://navs.store', 'https://truongha.site', 'https://polinder.xyz', 'https://crocan.store', 'https://mintervil.xyz', 'https://yieldmon.xyz', 'https://stainal.xyz', 'https://stroyen.xyz', 'https://velanor.xyz', 'https://bushidows.xyz', 'https://isgreat.xyz', 'https://thuanannew1.store', 'https://loton1.store', 'https://ladantel.xyz', 'https://vidual.xyz', 'https://radors.xyz', 'https://arweave.services.kyve.network', 'https://arweave.ar', 'https://ar.owlstake.com', 'https://rikimaru111.site', 'https://ar.perplex.finance', 'https://mrciga.com', 'https://claminala.xyz', 'https://hazmaniaxbt.online', 'https://pi314.xyz', 'https://cavgas.xyz', 'https://dtractusrpca.xyz', 'https://crbaa.xyz', 'https://hlldrk.shop', 'https://canduesed.me', 'https://yolgezer55.xyz', 'https://tefera.xyz', 'https://euraquilo.xyz', 'https://krayir.xyz', 'https://mustafakaya.xyz', 'https://beyzako.xyz', 'https://htonka.xyz', 'https://arceina.store', 'https://baristestnet.xyz', 'https://darksunrayz.store', 'https://babayagax.online', 'https://rodruquez.online', 'https://itsyalcin.xyz', 'https://alpt.autos', 'https://ruangnode.xyz', 'https://khaldrogo.site', 'https://karakartal.store', 'https://svgtmrgl.xyz', 'https://kabaoglu.xyz', 'https://boramir.store', 'https://iblis.store', 'https://sunkripto.site', 'https://mehteroglu.store', 'https://barburan.site', 'https://auquis.online', 'https://chocon.store', 'https://salakk.online', 'https://mustafakara.space', 'https://linaril.xyz', 'https://leechshop.com', 'https://kagithavlu.store', 'https://rtmpsunucu.online', 'https://ar.taskopru.xyz', 'https://terminatormbd.com', 'https://koltigin.xyz', 'https://0xyvz.xyz', 'https://kahvenodes.online', 'https://yukovskibot.com', 'https://0xsav.xyz', 'https://ar.riceinbucket.com', 'https://yusufaytn.xyz', 'https://2save.xyz', 'https://rollape.com.tr', 'https://koniq.xyz', 'https://ainodes.xyz', 'https://arweave.auduge.com', 'https://ar.0xskyeagle.com', 'https://ar.ionode.online', 'https://wenairdropsir.store', 'https://ar.bearnode.xyz', 'https://fisneci.com', 'https://ar-node.megastake.org', 'https://astrocosmos.website', 'https://ar.secret-network.xyz', 'https://adora0x0.xyz', 'https://ar-testnet.p10node.com', 'https://ar.satoshispalace.casino', 'https://imtran.site', 'https://katsumii.xyz', 'https://nodebeta.site', 'https://blockchain-ario.store', 'https://ario.dasamuka.xyz', 'https://kt10vip.online', 'https://thanhapple.store', 'https://meocon.store', 'https://commissar.xyz', 'https://gisela-arg.xyz', 'https://sadas655.xyz', 'https://kenyaligeralt.xyz', 'https://ruyisu.net', 'https://0xmonyaaa.xyz', 'https://zirhelp.lol', 'https://gmajorscale.xyz', 'https://g8way.0rbit.co', 'https://misatoshi.pics', 'https://clyapp.xyz', 'https://dilsinay.online', 'https://secondtornado.xyz', 'https://mpsnode.online', 'https://gateway.getweave.org', 'https://comrat32.xyz', 'https://konobbeybackend.online', 'https://nodecoyote.xyz', 'https://sabrig1480.xyz', 'https://kingsharald.xyz', 'https://blockchainzk.website', 'https://vevivo.xyz', 'https://software0x.website', 'https://dasamuka.cloud', 'https://shapezero.xyz', 'https://bootstrap.lol', 'https://canduesed.xyz', 'https://nodeinvite.xyz', 'https://lethuan.xyz', 'https://bburan.xyz', 'https://velaryon.xyz', 'https://anch0r.com', 'https://thecoldblooded.online', 'https://moruehoca.online', 'https://cahil.store', 'https://dnsarz.wtf', 'https://rerererararags.store', 'https://validatorario.xyz', 'https://sefaaa.online', 'https://ahmkah.online', 'https://thecoldblooded.store', 'https://diafora.tech', 'https://berso.store', 'https://moruehoca.store', 'https://dilsinay2814.online', 'https://mutu.lol', 'https://cetinsefa.online', 'https://validatario.xyz', 'https://aantop.xyz', 'https://enesss.online', 'https://graski.xyz', 'https://wanr.top', 'https://arnode.cfd', 'https://aslanas01.xyz', 'https://shadow39.online', 'https://jaxtothehell.xyz', 'https://parkdongfeng.store', 'https://r4dn.tech', 'https://darthlyrex.xyz', 'https://acanpolat.xyz', 'https://arnode.xyz', 'https://prowsemre.online', 'https://nodevietnam.com', 'https://sygnblock.xyz', 'https://bodhiirozt.xyz', 'https://coinhunterstr.site', 'https://techvenience.net', 'https://apayro.xyz', 'https://anaraydinli.xyz', 'https://mrcetin03.store', 'https://cakonline.xyz', 'https://budavlebac.online', 'https://loriscant.site', 'https://0xsaitomo.xyz', 'https://neuweltgeld.xyz', 'https://arlogmein.xyz', 'https://arendor.xyz', 'https://ariozerowave.my.id', 'https://webraizo.online', 'https://xiaocloud.site', 'https://thekayz.xyz', 'https://captsuck.xyz', 'https://minhbear.xyz', 'https://Phuc.top', 'https://ibrahimdirik.xyz', 'https://sedat07.xyz', 'https://herculesnode.shop', 'https://cayu7pa.xyz', 'https://mahcubyan.xyz', 'https://0xknowledge.store', 'https://testnetnodes.xyz', 'https://gurkanceltin.online', 'https://stevnode.site', 'https://ongtrong.xyz', 'https://kecil.tech', 'https://myphamalma.com', 'https://lanchiaw.xyz', 'https://getblock.store', 'https://emireray.shop', 'https://lobosqlinc.site', 'https://polkasub.site', 'https://shapezero.site', 'https://ario.stake.nexus', 'https://digitclone.online', 'https://lostgame.online', 'https://mutu.pro', 'https://ar-dreamnode.xyz', 'https://diafora.site', 'https://aleko0o.store', 'https://vn-sti.top', 'https://flexibleee.xyz', 'https://soulbreaker.xyz', 'https://parafmax.site', 'https://omersukrubektas.online', 'https://node69.site', 'https://mertorakk.xyz', 'https://kanan1.shop', 'https://bsckapp.store', 'https://arweave.validator.wiki', 'https://arbr.pro', 'https://kiem-tran.tech', 'https://dnsarz.site', 'https://arweaveblock.com', 'https://didzcover.world', 'https://bambik.online', 'https://deknow.top', 'https://ar.alwaysbedream.dev', 'https://lobibo.online', 'https://teoteovivi.store', 'https://herculesnode.online', 'https://djeverasa.xyz', 'https://codehodl.xyz', 'https://kittyverse.skin', 'https://aothecomputer.xyz', 'https://ario-testnet.us.nodefleet.org', 'https://exodusdiablo.xyz', 'https://dwentz.site', 'https://iogate.uk', 'https://stonkson.xyz', 'https://iogate.co.uk', 'https://aksamlan.xyz', 'https://vrising.site', 'https://ozzcanx.xyz', 'https://flashwayne.online', 'https://utkububa.xyz', 'https://apeweave.com', 'https://nodebiz.site', 'https://arioarioario.online', 'https://ahmkahvalidator.xyz', 'https://nodehub.site', 'https://ar.ilaybilge.xyz', 'https://redwhiteconnect.xyz', 'https://software0x.space', 'https://snafyr.xyz', 'https://anti-mage01.store', 'https://ioar.xyz', 'https://flechemano.com', 'https://spectre01.site', 'https://alexxis.store', 'https://maclaurino.xyz', 'https://bicem.xyz', 'https://torku.xyz', 'https://ar.kiranli.xyz', 'https://vnnode.top', 'https://sarlos.site', 'https://frogzz.xyz', 'https://sakultarollapp.site', 'https://nodezeta.site', 'https://bootstrap.icu', 'https://slatrokh.xyz', 'https://blessingway.xyz', 'https://alicans.online', 'https://practicers.xyz', 'https://senzura.xyz', 'https://campnode.xyz', 'https://elessardarken.xyz', 'https://treexyz.site', 'https://doflamingo.xyz', 'https://recepgocmen.xyz', 'https://nodetitan.site', 'https://sametyuksel.xyz', 'https://hexamz.tech', 'https://coshift.xyz', 'https://mrheracles.online', 'https://vikanren.buzz', 'https://vevivofficial.xyz', 'https://ariogateway.online', 'https://arnode.site', 'https://weaversnodes.info', 'https://chaintech.site', 'https://zerolight.online', 'https://adn79.pro', 'https://nodetester.com', 'https://regaret.xyz', 'https://kazazel.xyz', 'https://0xkullanici.online', 'https://erenynk.xyz', 'https://nodepepe.site', 'https://ar.tomris.xyz', 'https://ar.phuongvusolution.com', 'https://mulosbron.xyz', 'https://gatewaykeeper.net', 'https://zekkava.space', 'https://kunacan.xyz', 'https://grenimo.click', 'https://nodechecker.xyz', 'https://yakupgs.online', 'https://ar-arweave.xyz', 'https://nodevip.site', 'https://love4src.com', 'https://eaddaa.website', 'https://sowyer.xyz', 'https://ivandivandelen.online', 'https://stajertestnetci.site', 'https://pentav.site', 'https://ahnetd.online', 'https://zionalc.online', 'https://cyanalp.cfd', 'https://stilucky.top', 'https://ykpbb.xyz', 'https://mdbmesutmdb.shop', 'https://erenkurt.site', 'https://murod.xyz', 'https://aralper.xyz', 'https://kingsharaldoperator.xyz', 'https://merttemizer.xyz', 'https://tekin86.online', 'https://ademtor.xyz', 'https://kyotoorbust.site', 'https://cmdexe.xyz', 'https://sooneraydin.xyz', 'https://avempace.xyz', 'https://ario.oceanprotocol.com', 'https://stevnode.space', 'https://spacemarko.xyz', 'https://ariobrain.xyz', 'https://xacminh.store', 'https://hupso.store', 'https://kurabi.space', 'https://castilan.site', 'https://rockndefi.xyz', 'https://aoweave.tech', 'https://thique1.site', 'https://bobinstein.com', 'https://imontral.xyz', 'https://decentralizeguys.store', 'https://11.ario.p10node.onl', 'https://mydeepstate.space', 'https://denual.xyz', 'https://meditationlove.space', 'https://cayvl.store', 'https://dymwizard.space', 'https://giantmoodeng.site', 'https://arweave.fllstck.dev', 'https://ronganminh.site', 'https://owlorangejuice.bar', 'https://5.ario.p10node.onl', 'https://rufetnaliyev.store', 'https://0.ario.p10node.onl', 'https://tekin86.site', 'https://siyantest.shop', 'https://imyadomena.online', 'https://6.ario.p10node.onl', 'https://txhoang.site', 'https://hoanminh.site', 'https://renekta.xyz', 'https://kollmz.site', 'https://boy75.store', 'https://phuxuan1.site', 'https://khuachina.site', 'https://arweave.ddns.berlin', 'https://zerosettle.xyz', 'https://decaprios.xyz', 'https://ario.arweave.io.vn', 'https://omies.space', 'https://junnew.site', 'https://birinci.space', 'https://ario.koltigin.xyz', 'https://huenews.space', 'https://xuankhai.site', 'https://ario.io.vn', 'https://communitynode.dnshome.eu', 'https://llct.space', 'https://nguyenthi.site', 'https://vf6plus.site', 'https://ar.qavurdagli.online', 'https://ar8.innostack.xyz', 'https://ar2.noddex.com', 'https://hupsoapsoap.store', 'https://4.ario.0x0.io.vn', 'https://4.ario.ario.io.vn', 'https://ar9.innostack.xyz', 'https://decentralizelocation.space', 'https://permaweb.cfd', 'https://arnexus.cfd', 'https://ar6.oohgroup.vn', 'https://ar7.noddex.com', 'https://khang.pro', 'https://ar2.innostack.xyz', 'https://eatcleanwater.space', 'https://ahmetcan.store', 'https://ilgazsoy.store', 'https://ario.ario.io.vn', 'https://4.ario.ctytanviet.vn', 'https://dyorfinance.site', 'https://ar7.oohgroup.vn', 'https://ar8.noddex.com', 'https://dumdump.space', 'https://ar1.oohgroup.vn', 'https://trinhsatkhonggianmang.space', 'https://mintlamay.site', 'https://4.ario.arweave.io.vn', 'https://khoaito.site', 'https://kakalot.online', 'https://seeyouselfboy.store', 'https://dimori.space', 'https://trinhsatdaitai.space', 'https://voinetwork.site', 'https://altseason.space', 'https://dependenceboys.site', 'https://retardo.site', 'https://ario3.thd.io.vn', 'https://paxjudeica.space', 'https://cyberfly.store', 'https://noblesilence.site', 'https://mimboku.space', 'https://kgenesys.space', 'https://phatriet.site', 'https://tamduong.site', 'https://cashwaterflow.space', 'https://ar6.innostack.xyz', 'https://ckiiem.site', 'https://4.ario.aoar.io.vn', 'https://aoar.io.vn', 'https://ar12.innostack.xyz', 'https://4.ario.thd.io.vn', 'https://ario2.aoar.io.vn', 'https://thanhapple.site', 'https://hinhsu-no1.site', 'https://arweave.net', 'https://ar3.noddex.com', 'https://ar5.noddex.com', 'https://ar1.stilucky.xyz', 'https://ar2.stilucky.xyz', 'https://ar3.stilucky.xyz', 'https://ar4.stilucky.xyz', 'https://ario10.aoar.io.vn', 'https://ar10.stilucky.xyz', 'https://ar11.stilucky.xyz', 'https://ar16.stilucky.xyz', 'https://g1.vnar.xyz', 'https://ar18.stilucky.xyz', 'https://ar19.stilucky.xyz', 'https://ar17.stilucky.xyz', 'https://g2.vnar.xyz', 'https://g4.vnar.xyz', 'https://g5.vnar.xyz', 'https://g3.vnar.xyz', 'https://g7.vnar.xyz', 'https://g8.vnar.xyz', 'https://g9.vnar.xyz', 'https://g14.vnar.xyz', 'https://g10.vnar.xyz', 'https://g6.vnar.xyz', 'https://g17.vnar.xyz', 'https://g15.vnar.xyz', 'https://g20.vnar.xyz', 'https://g16.vnar.xyz', 'https://g18.vnar.xyz', 'https://g19.vnar.xyz', 'https://ar20.stilucky.xyz', 'https://fudcrypto.space', 'https://arweave.tokyo', 'https://g21.vnar.xyz', 'https://ar21.stilucky.xyz', 'https://g22.vnar.xyz', 'https://ar23.stilucky.xyz', 'https://ar22.stilucky.xyz', 'https://ar24.stilucky.xyz', 'https://g24.vnar.xyz', 'https://g23.vnar.xyz', 'https://g12.vnar.xyz', 'https://ar5.stilucky.xyz', 'https://ar6.stilucky.xyz', 'https://ar.ominas.ovh', 'https://ar2.ominas.ovh', 'https://alicans.site', 'https://arweave.zelf.world', 'https://ar8.oohgroup.vn', 'https://ar4.noddex.com', 'https://ar2.oohgroup.vn', 'https://liluandinhcao.store', 'https://semedo.site', 'https://umutdogan.space', 'https://flechemano.online', 'https://ario-gateway.nethermind.dev', 'https://ario.bayur.net', 'https://onetwothreemoving.space', 'https://g11.vnar.xyz', 'https://1mblock.space', 'https://ar5.oohgroup.vn', 'https://g13.vnar.xyz', 'https://ar12.stilucky.xyz', 'https://ar15.stilucky.xyz', 'https://ar8.stilucky.xyz', 'https://ar14.stilucky.xyz', 'https://brownmoodeng.store', 'https://ar13.stilucky.xyz', 'https://ar9.stilucky.xyz', 'https://araoai.com', 'https://ong3.xyz', 'https://sulapan.com', 'https://kt10.site', 'https://germancoin.space', 'https://donkichot.space', 'https://nguyenhoang1.site', 'https://sultanfateh.store', 'https://bienchecung.store', 'https://emilywalker.space', 'https://beyondstars.store', 'https://shreksson.store', 'https://2.ario.p10node.onl', 'https://gubidik.store', 'https://perma-swap.space', 'https://donchon.store', 'https://coshiftera.xyz', 'https://ar5.innostack.xyz', 'https://drrufana.online', 'https://arlink.xyz', 'https://loriscant.space', 'https://10.ario.p10node.onl', 'https://greenxanh.xyz', 'https://youmust.store', 'https://dangkhoi-ken.store', 'https://tefera.site', 'https://ario-lol.store', 'https://dieulenh.site', 'https://geralt.space', 'https://ar15.innostack.xyz', 'https://pentav.cloud', 'https://aoshield.online', 'https://fromchinatoeu.store', 'https://ar7.innostack.xyz', 'https://12.ario.p10node.onl', 'https://campnodesa.xyz', 'https://7.ario.p10node.onl', 'https://perma-web.store', 'https://altugario.space', 'https://phugiavip.store', 'https://ar4.innostack.xyz', 'https://sieucapchinhtri.store', 'https://05.aoar.io.vn']
