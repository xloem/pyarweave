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


from ar import Wallet, DataItem, ANS104DataItemHeader, Bundle
import pytest

import sys
from jose.utils import base64url_decode

def test_serialize_unsigned():
    dataitem = DataItem(ANS104DataItemHeader(owner = wallet.raw_owner, anchor = b'00000000000000000000000000000000', tags = [{'name':b'name','value':b'value'}]), data = b'Hello, world.')
    assert dataitem.tobytes() == (
        b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        b'\x00\x00\x82o\xcc\x14\xe3\x1a\xd4j\x10[T\xad\xe6fJod\x94.oM\xb4g' +
        b'xih\xae\x0eb\xe8\xa8\x87`K\x86\x9c;\xd3\xdb\x7f\xde<{\x80\x17;N' +
        b'\x8a\x1cn*\xa3h \x8ew\x17\xa1a<s\x83i\xab]\x17G\xeb%\xc2\xda\xa7' +
        b'.\x8c_i\x89&|\x96(\x81!"-\xc6*2d#\xa1=\xea+}W\xc0S4\x81\xe9\xdd' +
        b'\xe3\xf6|\xa4q\x96\xd5aw\xe8 P\x97\xe4a\x82>sLC(/ug{\xea\x1a#8' +
        b'\x14\xa5\xde\xbb\xddUM\xde\xcb\xd2\xb5\xca\xdaWe]#\xb4\xf5\x91' +
        b'\x83\xe1k\xac\xd1\xc3\xbba\x8f\x08\x05\xf74p\xfc\x950{\xe1P\xce' +
        b'\xb5\xc4\xe1\xb4\xe1\x0c\xc7\x82\xb7\xa1\xb3\xe1\xc3\x1dUZ\xaaZ' +
        b'\x11\x01\x05f_*\xa8\x94\xc5\xfe\x15\x8d\xdf\xa4\x94\xa4\x18C\xb5' +
        b'\xef\xf8\x7f\xee=\xa4\xc1\x84\xbbK\xc9\xb5\xa8\x84@\xb7\xd6g\xb2' +
        b'\'\x91W\xa1z\xdcBQs\xe8\x04\xea\x96b\xb9\x19Sol\x12\xbf`J\xb5' +
        b'\xa3]V[\xe3 G\xdc+)\x1f\xe1\x18\x13\xf3\x05<J\x00\x89\x81R\xc4' +
        b'\xd5\x08-\x9f\x7fJ]j\xb9mQmO3g\x8c\xf8\x16\x951\xed\xa2\xf76\x89' +
        b'*0\xf0\xf77\x08)\xcb\xf8\x8f\xdb\xe3j\xa5\xc3\xa3vhO|\xbbJ\xf0Ph' +
        b'\x13\xf2oK\x9b\xd8a\xea\x1f\xfdp\x06\x1a\xa5o+?\xc9m\x97;\x04' +
        b'\x11n\x91jq [\xc2F\\\x92\x8f\x01\x84gO\xc0\x91\x00\x964\xa8\xfc' +
        b'\xf1\x93\x044}<\x8d\xd9\xff\x1f!nhZ\xc69I5*N7\xc5\xe9\xc6\x06' +
        b'\x1dD\x9a\x86\xab.w\xbe`\xd8mS5\xba\x8e\xcc=\xbe\xc5\x0fV\xd7' +
        b'\xbc%\xbed\x0b!\x18\xc7\x0c\x05\x93\xf8\x04u\x0f\xf6\x9a\xc8\x10' +
        b'\xc7O)\x93\x98\x19\xbb\xccD\x16\xbc\x93-)j\xc0\xc0/m\x8bmq+C\x82' +
        b'3\xe4Q\x81O\x1f\xde\x19h\x98{\x83\x8d\x8a\xa9#\xcdJEu)\x9d`\xbb' +
        b'\x80&\xc7\x9c\x9b\xe0\x922\xb2\xc0\xe8\'\xca\xf1\x11\xa8M/\xd0' +
        b'\x81\xc7\x90T\\\xd2\x83\xe9\x00\x0100000000000000000000000000000' +
        b'000\x01\x00\x00\x00\x00\x00\x00\x00\r\x00\x00\x00\x00\x00\x00' +
        b'\x00\x02\x08name\nvalue\x00Hello, world.'
    )

    dataitem.sign(wallet.rsa)
    dataitem = DataItem.frombytes(dataitem.tobytes())
    assert dataitem.verify()

def test_ans104_verification():
    ans104_bytes = (
        b'\x01\x00\x89%\xb6\x8d\x95\xce\xc2dz\x8b;\x82\xbcw\xf7\x0b5\xce' +
        b'\x95\x94\xc4\xb3.m\xb3\xbfwM\xaf\xa08O\x8a\x12\x7f\xfa\x18\xcbU' +
        b'\xfa\xf4\xfc0.\x1dF*q\xc6\xb4\x96\xdb\x95\xf2\xfd)\x13L\xc2\xac' +
        b'\x89|\x0f\xdd\tOP`\xc0\x0b)\xb7S\x16^G\xd6\x89\xc9\xbe\x12\xf6' +
        b'\x9a \xa3\x1a\x1cm5\xed\xb4\xfaV\xf92\r\x9d\xfe\xbc\x1a\\\x802' +
        b'\x8d\xa2\x0c\xdd\xd6\xa3\xd6\x17e\xb3s\xc6m\xaf\x97\xd4g\x95\xd6' +
        b'\xc2\x07\xf1\x03\xd3v\xa3\xef\x17B`\x94\xd3\x7f\x91\x0f\xb9\x18' +
        b'\x1cSy\x92\x8e\xae\x82\xf8}\xe9\x13\x056\x96qW\x99\x82+\\k1d\xb5' +
        b'R\xbc\x184\x04\x7fQ\xa1L1G\x88\x89\xdd\x0e\xbfq\xadR\xbe\xd3+' +
        b'\xa6b\xc7\x94\x9a\xff\xc7-\x85\xe23--\x8e\x153s\x9b\x00\xc82\xf8' +
        b'\xf2-I\xbd\xfd\xc3\x1e\xc2\x91\xb7\xca\xe0\xe1y7&-=\xa67\xbf\xc9' +
        b'\xe3\x91?U\xb7\x05\\}|\x11P/\xe7\x02\xe2\xbf\xbeg\xaa\xa8\xa4b' +
        b'\xe3\xdc\xde\x0f\x01\xde%gFc\x97>\xb8\xdc\x10\x86\x03\x11\xf1' +
        b'\xd1X\\\xbe\xdc\x88Nv+\xd3=\xf4|)\xce?\x15\xf8\xed\x868\x8d\xe1^' +
        b'\x9e\xd9\xf1\x99\xfcGZ@\xf3B\xfe\x0c\x1f\xf5\xcb\xb1\xe7\x81\xad' +
        b'a\x96a\n\xe22;\xf9\x80_O\xcaDZ\x93\xbf{\xef\xc2\x05\xd8kI\x9a' +
        b'\xc0\x94\x9f5\x15\xbd\x04\xfc\x03\xba\x91\x8f\x00+N\xf0\x93Z\xdd' +
        b'\x99V \x1e\xd5G\xc0\x11\xd0M\xab0\xea&\xf8\x1b\\\xcd\xdf\x15\xf1' +
        b'/n\x12\x0f\x03\xa9-\xcd\xc0\xc4\x9ab\xfa\xdc\xd4t\xe7\x89A\x98' +
        b'\xf07\x1aI\xd1!\x99\xc5\xa9\t\xde?h@\xbc\xc0\xd0\x8c\xa5\xedt\n' +
        b'\xf5q\x90\xba\x15\x1c\x8a\xc9bK\xc8\xab\xf9\x8db|\xa3\xfdjGUR=RB' +
        b'y\xe8{|\xdav\xb9\xc7\x03\xeb\xf1\x0b\xa8Q\xa4\xe2\xa5\xf3\xb9' +
        b'\x8d\xb1<\x07p&\xb0\x83H<\xedIxZ\xe5\n\xa8\xe7s\xa2\xbf\xaf\xdey' +
        b'D$EQ\x1f *\xbf\x80JI"T\xb8:\xd1\x80\xe3\xd2\x83s,=\x8e\xdd\x94>{' +
        b'\x92\x83\xe0\x87\x8f\x04\xd4q\xea$M\xdb=_\x88k\xf8\xa6)\xe4\x14' +
        b'\x8d\xd89\xb5\xe0\x926\x0e\xb8\xd7&\xef\xb7\xaan\xc5\xe8~f\xb4h' +
        b'\x93\x1d\x8b\xc7\x14\x17\xd2N\xdcm\x0b\xfd\xe51QPSCi\x01|b\x92' +
        b'\xed2\x97\xe20\xcft\xa8\xf7E\xe9lp\xd2}\x8eyU}\xd1\x111\x14V#' +
        b'\x95\xef(\x91\xee\xaf\xd5\xdf\x8d\xef/\xc0\x94M\xb8I,B\xa6w|\xf9' +
        b'-\x93\xca7o\xd1&\np\xa3\xfb=Wu\x12?\xb8m\xc3\x95\xe7\xd9\x8d\xea' +
        b'H68\xe3\xc9\xf5@\x92\xa1\x19\x1e\xa4\x8c)\xd9e~\xab/\x8b\xb6\xd6' +
        b'\xca\xae\xb7B\xb4\r\'\xb1\xef\x89\x92\xc0\x14\xc3\xf6\xd0\x18' +
        b'\x1c6)I\x94\x9c\xa4\x85\xec9\xc9\x920\xc2\xfa\xb0[\'\x12\xb0\xd6' +
        b'\xd4\xcb\xb8\x8c\xf4\x1da\xb1\x84\xb8\xd1\xe8\xb0`\xda\xcc\xb7' +
        b'\xa7\x82\xc9}\xd6\xdd\xa0u\xf6K\x03\xd3\xa1\x82\x17\x18\xd2\x1eb' +
        b'\xee\x975\xdfV\x89\xd1\x0f\x0e\x9f\x1c\xac\x03|\x02\x8f\xf8\xdb' +
        b'\x06Jm\xae.\xe9bA\x070\xd5\xfd\x91\x10\x10\xef\x12#\x02`\x13c' +
        b'\x80\xda\x1b\x9e\xc9\x9d\xca\xea\xd7{\xcfFAQ\x1d\xc7\x1d\xd7W' +
        b'\xaa\x8f\n;\xbf\xc4P\x9d\xd9(\xeb\x86M{\xf4F)\x18:yH\x92\xfa\xec' +
        b'&\x83e\x0cY}\xbc\t\x05\xe0\xaf\xc8\x1d\x82P9\x86\x0f\xda\xa9\xe2' +
        b'9/6f3\xc6\xb3\x96,H"e1\xf4\n\xaa\xbf47]\x99\x92\x0b\xe8HR\x16' +
        b'\x9d\xaf\x1a\x05\xfdh\x08s\xb2\xb1\xb8)\x1a\x92\xf4\xfe\x99\xf7' +
        b'\xa1\xda\x06\x0e\xe9\x82%\xbe\x1a\x8d\x88\x02\xcb\x04\xe9\xe6' +
        b'\xc8\xf1\x1d\x8a`\xd5\xd5\xc8\x8b~\xdb\x84\x85\x99T\x9c\x9ex\xf6' +
        b'\xe2\xbff\xf6\xf85R\t>\x01\xfd\xf9\x17\x86\x1c\xc7k\xfe\xabR\x9a' +
        b'&H\xadn\xe9\xd7\xf3\xee\xb1\xcb\xf6>"\xdf^\x96\xff\xc26\xe1w\xa5' +
        b'H^\x07\xae\xfa \x84-\x17\xf6j\n\xcc\x9c\xa2\xf3\x931m:\xa1\xcdM' +
        b'\x10\x8d\xc21\xb4\x82\x1e\xb2\x91Lo6IQ\x8c\xba17=\x80q\xd8\xd5v' +
        b'\xaa\xc7\x00\x00\x07\x00\x00\x00\x00\x00\x00\x00\xdb\x00\x00\x00' +
        b'\x00\x00\x00\x00\x0e\x08Type\x08file\x0eBundler8https://node2.bu' +
        b'ndlr.network\x0cBundle\x0cans104\x14User-Agent\x08arkb$User-Agen' +
        b't-Version\x0c1.1.56\x18Content-Type0application/octet-stream\x12' +
        b'File-Hash\x80\x011bbc5db9f969c26aef492af5016a719e496e038fb1a2b51' +
        b'd11daf93b639908f2\x00x\x01+)JMU06`01\x00\x02\x05\xa3\xe4T\x86' +
        b'\xcco\x96\x1c\xc7\xbc\xe6O\xf6}\xdd\x93\x962%_\x90q\xb2\xb1\x12' +
        b'\x00\xe5\xcb\x0c\xaf'
    )
    dataitem = DataItem.frombytes(ans104_bytes)
    assert dataitem.verify()
    assert dataitem.tobytes() == ans104_bytes

def test_ans102_verification():
    ans102_json = (
        {
            "items": [
                {
                    "owner": "wJ-mV2BK3Zs7Z-aHiZ1obA0oBXS9xeWtVNOme6pOJoNRiH8b4RDp71Z-KG1pzYaLRyy_aLxhSPrioJ3MACdGlcAkR1Uxz8gCC1Smswc3yWLcc9WP25W9jFJ7l7CLQ3cLL9PMqVikL25w3CMqo0fwEIdQBSaZr1R7x7tM-gXNmOffZEEVFZZBCzhMYMOAiVqGvxEOYG4jgOTL0tnPCptgoYY-XtF-egtUDCYGgq7J3DiOCj7pf6bcH1qBfkOwQNJdG1ZCmR9xrmUPAMQy6CzeyZ0DzYYyc-ZOytfNuAU-gGEtQanepZpGTw1jrd3HKmpmddYKbqpjYwG-wsSIIxn3B1Ui5jDC18R2JzxypQGrZj_fQ5jYy73OlYtxBrM50GQDEADbelHyngbGnbwvGkwN4FGfd-QsjAfGIkRBAllTXeToHsCXTJ-ReEZvHRWg9ZQolxU74QM3OjxwpKTtHIyKOJGEGfe6SaEdIysKeyZmvzYRtgrX2FVJIIzCJfaQG82NfxJF2mJBZf8_aI7SN92Z-EryoK8Fi9fsrua12haFLtuGDVwKsLv3vOkdNCITycAVaSo_j567sz-XF-BzJixnQn4wePlyqRZ82O7N9-yrIxYYttEliofYxTSU96r5qJzD_2N9XjdxNgOKtC48SXgaLnJlUD8xQpeaNOEGEH6Roq8",
                    "target": "",
                    "nonce": "",
                    "tags": [
                        {
                            "name": "QXBwbGljYXRpb24",
                            "value": "S1lWRSAtIERFVg"
                        },
                        {
                            "name": "UG9vbA",
                            "value": "OGNxMXdialdITmlQZzdHd1lwb0RUMm05SFg5OUxZN3RrbFJRV2ZoMUw2Yw"
                        },
                        {
                            "name": "QmxvY2s",
                            "value": "MHhjNDJlZjIyYjAzM2YwYzBlYzdjYTU2OWQ3NjE3OWFkNTdjNDZjOTkwYTczNDY3YzQyZDA4MTk0MWI2ODUxYTBj"
                        },
                        {
                            "name": "SGVpZ2h0",
                            "value": "MzAxMDUyOQ"
                        },
                        {
                            "name": "VHJhbnNhY3Rpb24",
                            "value": "MHgxZDJiMzYxNDFlMWVlNGUyNjBkNjc3Y2UxNDQxOTgyNDg1MDg2NGM3NjBiMzVkZTMxMzI0YWUxODgzZjg0NWY0"
                        }
                    ],
                    "data": "eyJibG9ja0V4dHJhRGF0YSI6IjB4IiwiZGlmZmljdWx0eSI6IjEiLCJleHREYXRhSGFzaCI6IjB4NTZlODFmMTcxYmNjNTVhNmZmODM0NWU2OTJjMGY4NmU1YjQ4ZTAxYjk5NmNhZGMwMDE2MjJmYjVlMzYzYjQyMSIsImV4dHJhRGF0YSI6IjB4IiwiZ2FzTGltaXQiOjgwMDAwMDAsImdhc1VzZWQiOjIxMDAwLCJoYXNoIjoiMHhjNDJlZjIyYjAzM2YwYzBlYzdjYTU2OWQ3NjE3OWFkNTdjNDZjOTkwYTczNDY3YzQyZDA4MTk0MWI2ODUxYTBjIiwibG9nc0Jsb29tIjoiMHgwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMCIsIm1pbmVyIjoiMHgwMTAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIiwibWl4SGFzaCI6IjB4MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMCIsIm5vbmNlIjoiMHgwMDAwMDAwMDAwMDAwMDAwIiwibnVtYmVyIjozMDEwNTI5LCJwYXJlbnRIYXNoIjoiMHg2MzJlODUwZGZmZWZmYzFhNjdlZmYzNTY5NjFlOWFiYjUyMWVlYjYzMWE5NTlmYmUzMWM4ZWViZGQxZmM2MmY3IiwicmVjZWlwdHNSb290IjoiMHgwNTZiMjNmYmJhNDgwNjk2YjY1ZmU1YTU5YjhmMjE0OGExMjk5MTAzYzRmNTdkZjgzOTIzM2FmMmNmNGNhMmQyIiwic2hhM1VuY2xlcyI6IjB4MWRjYzRkZThkZWM3NWQ3YWFiODViNTY3YjZjY2Q0MWFkMzEyNDUxYjk0OGE3NDEzZjBhMTQyZmQ0MGQ0OTM0NyIsInNpemUiOjY2NCwic3RhdGVSb290IjoiMHhiOWZjNWQxMjA2OGJjODQxNTgwZDU0MDIzZDdmYjE2YjhhMjNjN2NmNDRhZmVjZGE0MDU2MGQ4NTJlY2I4ZjBjIiwidGltZXN0YW1wIjoxNjI5MTM2NTY2LCJ0b3RhbERpZmZpY3VsdHkiOiIzMDEwNTI5IiwidHJhbnNhY3Rpb25zIjpbeyJibG9ja0hhc2giOiIweGM0MmVmMjJiMDMzZjBjMGVjN2NhNTY5ZDc2MTc5YWQ1N2M0NmM5OTBhNzM0NjdjNDJkMDgxOTQxYjY4NTFhMGMiLCJibG9ja051bWJlciI6MzAxMDUyOSwiZnJvbSI6IjB4MEQwNzA3OTYzOTUyZjJmQkE1OWREMDZmMmI0MjVhY2U0MGI0OTJGZSIsImdhcyI6NTAwMDAsImdhc1ByaWNlIjoiMjI1MDAwMDAwMDAwIiwiaGFzaCI6IjB4MWQyYjM2MTQxZTFlZTRlMjYwZDY3N2NlMTQ0MTk4MjQ4NTA4NjRjNzYwYjM1ZGUzMTMyNGFlMTg4M2Y4NDVmNCIsImlucHV0IjoiMHgiLCJub25jZSI6MjI3OSwidG8iOiIweDJCQzVEQzIxMEY2QUU0MDNkRTg5NUQwNjY1MDlERUZGRTkzMzUxODQiLCJ0cmFuc2FjdGlvbkluZGV4IjowLCJ2YWx1ZSI6IjE3NjE0NDAwMDAwMDAwMDAwMDAwIiwidHlwZSI6MCwidiI6IjB4MTUwZjciLCJyIjoiMHg5YWU3MTQ3ZjY4NGI0OTQ5MDQ1ODZhNWU1M2M1Njc4YTZkYTRkNDQyMDE1NGVmNWVhYzNiMGE5NjRiYjcxNjkwIiwicyI6IjB4NjlkOWY1YThhZTBlMTc4YzdhODg1N2I4Y2UyN2FmMTU0ZWVhMzc2Yzg5NDNmNzIyMTczMjU1NzQyOGQyZmVkNCJ9XSwidHJhbnNhY3Rpb25zUm9vdCI6IjB4ZTdkNDA5MGZlNTNmNTgwMjAyMzY0ZWUwOWFjYWUyOGViYWNmZjFiODlkMzY5ZGY1M2EyZTA1Y2NlZGZkYWJhNyIsInVuY2xlcyI6W119",
                    "signature": "mfycPwDLJvhiKy0TzL70D109uvopnXQIf1tWlF4G6h6k1eLHWrQnRLLa2sN3pI9a4lCdIko1QxY-qlzbXx61w3wBynXD8Wpr1Kx6eCgTyF6jaUBHhXv1XBIz8kLtpm7HRpQT4Mg9bqHscsYext0mNMX-xTD81ZdAkJ7WSMh2_W5Av3o_5rxtJwjHdvgWXGZGd3jq3t6cfzjj4yo7mGoBQ_U3fHCrLXHLHuMJy6nsq-CvJhDgkfgBm2Cl69O6pvZd0FKGn-xGdDGxy_zf7b_HuQAmiZbKhiZMVRpfxNiY0TKDwo1xztuX4EJGy-_2wJB02zCijTtSGrJkjtOfK0xpb-SN00ly7hkcypUmQH0Mv6xBDn1LwbuFZ1g0jgEGVDQAd6QM3l7aPXx-ZxYffE8HHD3xXJX5L8vPDuZ14H_Kq_DjKR8UIYf9GqLQNw8qyFi8BSCDi_zbZzMvLBvEvPj9eJMZHVZ-4o_YzmpHvvOxLrpxuXQLbq8Vn6NQcV71iiD6hHomyz1QYCDWiOironlpZVMsMv1LNY_Zh-A-1pCq0tY6GoNt3vLevWCgKxLVPq2MuzUC47YkSR7TJVlTnnA1dfRmNDaIFd7FcNzsKvzYtaQqAfCdHEVq6kwCbMO6Z_U4lr0WVtUFpNIwljyZ__MRF_qYWSG8dwt9jPb3brIOHpM",
                    "id": "EgrakUztxTUwDHkfRd57J6WikFpkr0cvXaF2X9ydQIY"
                },
                {
                    "owner": "wJ-mV2BK3Zs7Z-aHiZ1obA0oBXS9xeWtVNOme6pOJoNRiH8b4RDp71Z-KG1pzYaLRyy_aLxhSPrioJ3MACdGlcAkR1Uxz8gCC1Smswc3yWLcc9WP25W9jFJ7l7CLQ3cLL9PMqVikL25w3CMqo0fwEIdQBSaZr1R7x7tM-gXNmOffZEEVFZZBCzhMYMOAiVqGvxEOYG4jgOTL0tnPCptgoYY-XtF-egtUDCYGgq7J3DiOCj7pf6bcH1qBfkOwQNJdG1ZCmR9xrmUPAMQy6CzeyZ0DzYYyc-ZOytfNuAU-gGEtQanepZpGTw1jrd3HKmpmddYKbqpjYwG-wsSIIxn3B1Ui5jDC18R2JzxypQGrZj_fQ5jYy73OlYtxBrM50GQDEADbelHyngbGnbwvGkwN4FGfd-QsjAfGIkRBAllTXeToHsCXTJ-ReEZvHRWg9ZQolxU74QM3OjxwpKTtHIyKOJGEGfe6SaEdIysKeyZmvzYRtgrX2FVJIIzCJfaQG82NfxJF2mJBZf8_aI7SN92Z-EryoK8Fi9fsrua12haFLtuGDVwKsLv3vOkdNCITycAVaSo_j567sz-XF-BzJixnQn4wePlyqRZ82O7N9-yrIxYYttEliofYxTSU96r5qJzD_2N9XjdxNgOKtC48SXgaLnJlUD8xQpeaNOEGEH6Roq8",
                    "target": "",
                    "nonce": "",
                    "tags": [
                        {
                            "name": "QXBwbGljYXRpb24",
                            "value": "S1lWRSAtIERFVg"
                        },
                        {
                            "name": "UG9vbA",
                            "value": "OGNxMXdialdITmlQZzdHd1lwb0RUMm05SFg5OUxZN3RrbFJRV2ZoMUw2Yw"
                        },
                        {
                            "name": "QmxvY2s",
                            "value": "MHg3ZWM3ZWE3OTM1NGYzZGEyYjdjNGY0MjRjYmQ2MGI5YjEyNTdhMzk5N2Q4ZWJlOGRlZGY2ODY0MDY5MGNiYmEz"
                        },
                        {
                            "name": "SGVpZ2h0",
                            "value": "MzAxMDUzMA"
                        },
                        {
                            "name": "VHJhbnNhY3Rpb24",
                            "value": "MHg4OTg1NmM0Y2RlNjQxYzAxM2I1ZTNjMjU0MTc2OGM4MThjM2JlNWFjNmE3MzBiMjFmZGJlZDZjMTEyYzI0ZTJl"
                        }
                    ],
                    "data": "eyJibG9ja0V4dHJhRGF0YSI6IjB4IiwiZGlmZmljdWx0eSI6IjEiLCJleHREYXRhSGFzaCI6IjB4NTZlODFmMTcxYmNjNTVhNmZmODM0NWU2OTJjMGY4NmU1YjQ4ZTAxYjk5NmNhZGMwMDE2MjJmYjVlMzYzYjQyMSIsImV4dHJhRGF0YSI6IjB4IiwiZ2FzTGltaXQiOjgwMDAwMDAsImdhc1VzZWQiOjQ2NjIxLCJoYXNoIjoiMHg3ZWM3ZWE3OTM1NGYzZGEyYjdjNGY0MjRjYmQ2MGI5YjEyNTdhMzk5N2Q4ZWJlOGRlZGY2ODY0MDY5MGNiYmEzIiwibG9nc0Jsb29tIjoiMHgwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA0MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDIwMDAwMDAwMDAwMDAwMDAwMDAyMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAyMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA0MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDEwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAyMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwODAwMDAwMDAwMDAwMDAwMDAwMDAwMDA0MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDQwMDAwMDAwMDAwMDAwMDAwMDAxMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMjAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMCIsIm1pbmVyIjoiMHgwMTAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIiwibWl4SGFzaCI6IjB4MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMCIsIm5vbmNlIjoiMHgwMDAwMDAwMDAwMDAwMDAwIiwibnVtYmVyIjozMDEwNTMwLCJwYXJlbnRIYXNoIjoiMHhjNDJlZjIyYjAzM2YwYzBlYzdjYTU2OWQ3NjE3OWFkNTdjNDZjOTkwYTczNDY3YzQyZDA4MTk0MWI2ODUxYTBjIiwicmVjZWlwdHNSb290IjoiMHhmNDAxMzlhZmNhZjkyOWM1MzczNGMzOWY1NzBlM2RmOGFjM2NjYzhkZGM3MTEwYWQyNzM5OWZmYTg5ZDJkNWYyIiwic2hhM1VuY2xlcyI6IjB4MWRjYzRkZThkZWM3NWQ3YWFiODViNTY3YjZjY2Q0MWFkMzEyNDUxYjk0OGE3NDEzZjBhMTQyZmQ0MGQ0OTM0NyIsInNpemUiOjcyNSwic3RhdGVSb290IjoiMHg1NmQwMjMyMWUyYjVkODVkMTlkNDUxMjcwODg2OGQ3NjliM2E2NTM3ZDc3ZmFlOGQ4ZTMzOTE2OGU3YjMxYTkwIiwidGltZXN0YW1wIjoxNjI5MTM2NTY5LCJ0b3RhbERpZmZpY3VsdHkiOiIzMDEwNTMwIiwidHJhbnNhY3Rpb25zIjpbeyJibG9ja0hhc2giOiIweDdlYzdlYTc5MzU0ZjNkYTJiN2M0ZjQyNGNiZDYwYjliMTI1N2EzOTk3ZDhlYmU4ZGVkZjY4NjQwNjkwY2JiYTMiLCJibG9ja051bWJlciI6MzAxMDUzMCwiZnJvbSI6IjB4MjVkNDhENzIyYzI2OTVkRjdhNTYyQjc5ODI3MjU1NDczQzA5ZjM5NCIsImdhcyI6NTEyODMsImdhc1ByaWNlIjoiMjI1MDAwMDAwMDAwIiwiaGFzaCI6IjB4ODk4NTZjNGNkZTY0MWMwMTNiNWUzYzI1NDE3NjhjODE4YzNiZTVhYzZhNzMwYjIxZmRiZWQ2YzExMmMyNGUyZSIsImlucHV0IjoiMHgwOTVlYTdiMzAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDllNGFhYmQyYjNlNjBlZTEzMjJlOTQzMDdkMDc3NmYyYzhlNmNmYmJmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmIiwibm9uY2UiOjM2OCwidG8iOiIweEUxQzExMEUxQjFiNEExZGVEMGNBZjNFNDJCZkJkYkI3YjVkN2NFMUMiLCJ0cmFuc2FjdGlvbkluZGV4IjowLCJ2YWx1ZSI6IjAiLCJ0eXBlIjowLCJ2IjoiMHgxNTBmOCIsInIiOiIweGRmNzRjYjdiZmMzMDQxNjQzMGFkMzVjY2YxOGIzM2U0MGQ4YjhhZWNkOTQyN2RhMjJmZDQ2ZjkzZDZhN2QzMmYiLCJzIjoiMHg1ZDgyYzU2ZjU5MjlmMDEyNDk2M2IzNTdjMjAyNzY4ZDQ0OTg1Y2QwNmVmMzQxNGJiMzMwMjY3MzVjZGIwNjMxIn1dLCJ0cmFuc2FjdGlvbnNSb290IjoiMHhjY2FkNWMyMjU2YjM5MjRmMGE5MmU4YzhjZWYyY2VmMWMyNTE5NDc3YjJhMmQ1YTQyNjQ3YzQ0ZWRmOGMwZWE5IiwidW5jbGVzIjpbXX0",
                    "signature": "exypSzenwXcgjbaxArKobH2yKpjUhD2NbZ_9aJO2NhzlOgisJsycNx-xooLlPadQi-d8hqkVFbP1CZ_NMCkjerf-iBiKIyzk5gdXJP8S7oyzJuocSLHcqcWtTVfh_LKJDc9uNANSSBAahaj_D_K3V90xG_RYTQTVJVeO3cGjXL87ZdReXzon5nniYLhOwZUYSi9MT43UEnOQihLaJvSBGUrLq1clVpgY-okv-g1bGB2CsM-AvJRanXOsNuVZ7pengds6QJ7SfLo9KnrmQKqe-Rv7coy_Yqisg8BuQ6GR66vU_miKBXSuzM_froDtDfjBT44VV-5dElkply0j_GM9ts9dq6YWjq_pNXLe9v-o10YqIPuYfq4nblV_lb2muOdr2kypmQAKabxPwEGe8wRAM7G0aZ3MdAs7Rw1TcNh31BQd3wM_zKNp3RZEE2pEetgKDSCwmg8gc7SSdPOszOtWYUtDzLVINSlz9QTXXBfjMHxFfUB4UL689hlxOjMY7T9UGsSPrjErYpLA5fgeeI0g8CLsrLTFV94Ye78p9wOmemN0ohk0dkqgIGm7l1pN8KVz3IZI40YQmHGCrO5B2RJ7QnB2KmZ6WG95QMPiavsxMZXCNpzCJaPMCpSX66cFJHzFngybIgIdLZHdzlxeAtZJzxzE-2zY2tQUd9c__cwiJc8",
                    "id": "MDEYtPsLIYzptwGG9-ZvZpg2ZtA8qztkIkPtSmKAj2I"
                }
            ]
        }
    )
    bundle = Bundle.fromjson(ans102_json)
    assert bundle.verify()
    assert bundle.tojson() == ans102_json

wallet = Wallet(jwk_data = {
    "kty": "RSA",
    "n":
        "gm_MFOMa1GoQW1St5mZKb2SULm9NtGd4aWiuDmLoqIdgS4acO9Pbf948e4AXO06K" +
        "HG4qo2ggjncXoWE8c4Npq10XR-slwtqnLoxfaYkmfJYogSEiLcYqMmQjoT3qK31X" +
        "wFM0gend4_Z8pHGW1WF36CBQl-Rhgj5zTEMoL3Vne-oaIzgUpd673VVN3svStcra" +
        "V2VdI7T1kYPha6zRw7thjwgF9zRw_JUwe-FQzrXE4bThDMeCt6Gz4cMdVVqqWhEB" +
        "BWZfKqiUxf4Vjd-klKQYQ7Xv-H_uPaTBhLtLybWohEC31meyJ5FXoXrcQlFz6ATq" +
        "lmK5GVNvbBK_YEq1o11WW-MgR9wrKR_hGBPzBTxKAImBUsTVCC2ff0pdarltUW1P" +
        "M2eM-BaVMe2i9zaJKjDw9zcIKcv4j9vjaqXDo3ZoT3y7SvBQaBPyb0ub2GHqH_1w" +
        "Bhqlbys_yW2XOwQRbpFqcSBbwkZcko8BhGdPwJEAljSo_PGTBDR9PI3Z_x8hbmha" +
        "xjlJNSpON8XpxgYdRJqGqy53vmDYbVM1uo7MPb7FD1bXvCW-ZAshGMcMBZP4BHUP" +
        "9prIEMdPKZOYGbvMRBa8ky0pasDAL22LbXErQ4Iz5FGBTx_eGWiYe4ONiqkjzUpF" +
        "dSmdYLuAJsecm-CSMrLA6CfK8RGoTS_QgceQVFzSg-k",
    "e": "AQAB",
    "d":
        "VafO8AR3UPhZx3AjRsLzrJTzDk8_SvILy8TXUFE5kbpczRwXqt4kLaMmOr_SAbtA" +
        "zQy3aVluz797QBnXlc-9a7AVIsBTqtLlqJa77VUIdhYxgSLeDAsvGKpUD4XWKjsE" +
        "jiLVv15xvUrXbTG-qF96W3AlHKn4MoyKMJGFaS0DCQehpHEmdgp_egiTu3RD6efN" +
        "XEkPUex6utVNCeWSVqPNnBzbtgu1Ctl53lAHPcd2A_ZBN6AowigpNV9o-u0wIzc5" +
        "YW9pnVzZXe_N_b3YmVftK0Hl1V1FeSuhfWV1jn-Bq1_Imb686mjyj_Nbgx10LPBV" +
        "kO5BuVTmPaVOEZDeGOqpU3WEkZpMw1NPP-Y6Z-V5n3Zy-FoXFautsQq5kWTC4Fc_" +
        "som5OImgeFRIUHFykQQvbo8fWBEl7lrpm0xt4LfxvFphae6m7cDDF_cIR8HGGQIj" +
        "vfLn9sflzbuFnhXaZpvMN5fwO-J6vFN108EdiZUAj5m8l9r5SzMaL5j9_d8SCiN7" +
        "aeDebZ_YluQvg8FV9D5ZK_HzUV4A8cK7UGvO4XNBYq-Ouo5WVBTDLhhUWUVStGhc" +
        "SWS4RFLFxBikEIybz2MzP_513-_-GNJEebqdPs2ckygQEcHYwdXLzQIDEEiF-Soq" +
        "CadSMvZVOwt7AFQMyAROSAwGOECn_M2mI0yl1Z2AZ7U",
    "p":
        "5vl76DAqbGDobTbBFz2P5ucv-kCEmk-vYS6j2n9jHZ9BQo1Fqng0MbUJZw3_4HRj" +
        "4N7etN2kiRzt-V4HElUNbZbI8qotH7ueqVKCrM7SUcMkhaVxTZZYTx6kD4f_X6Ki" +
        "rkDnxa_Rx4ONzOHzVXr5bl2mOEzS08FJ5P3fyQaexaVaoOKe3Nw0gE08SPpgQdkR" +
        "76ZL1FMEG2AF5FKBTR4kLvhQnXYqE-ZZydlyBa8vwynstgA-2kq2PZpT0JfNwF9l" +
        "kr9tW43HC8ZoJggjQDZ1YQg5ZmWoJS9OO9UJ1l2r7RGJl6wR5p9Nn68K0QlMxG2A" +
        "4kxRI9lgxJFReJrzz4z_kw",
    "q":
        "kJG0vkhHQ9EQnCCuDNp97GOYsxZhVQMoPFllbblxHwL05u3TldveYDId4vlPQt4-" +
        "S52METvvhhkdU6h4PmVCsGFpSW6xoz7uIA0oCRk3gWzviHYZMYlPnCPjIJNglYYX" +
        "q1LDaCVgEET6BJf7vtxv6olb4KnVP0W1Pdtoz2wZqnfPlfK71clj08NhmaBSYizZ" +
        "sHXPmOvwQoqZx0-6KLI9GdB0CcLQW5tOibywIjuFHgMUfl6WT6EBp3ibF6q3Q4WN" +
        "9OO3A9Vynex4ZNih0GpeAy9qVajjSlAowSsMmcBYK-nVlrbN1QCIcbqpYJew_W1L" +
        "aFCWsR2bFsrPJKENLvXEEw",
    "dp":
        "et52wqJ0vuiiXA7HkwRlu7B6Pkb6A1imdC0qbv5bDJP-VFfwmmmNYm_qy46P8qgX" +
        "xbTphg9uCp6AHaqeWmsyVHzk8uoCTSIymeJRr3nqOiJ0GEBVUK_M1HH5VmXDPO24" +
        "WrgeU3RfRSI_WaFNH8jmTYa1-LctZAYruAwxcq_54CxBVNqZJeZia2oqyquebwj5" +
        "WKH_Lrjms2VWXQpizFJfbzkbMVh9s85TL2RkGpAB-XEhAgSJavhZj9W8BnfqtQ5K" +
        "a1E37H80RphKKQklL3CI6pBEcKtdUkKi_IMs04NLBTbSGgQoFaXi1jJ4r5Ch7NBP" +
        "wpJUi5yEtKyVSXIshtl7zw",
    "dq":
        "SG3XgeWwXpelnLL6wFHO-NnFLSQvS2ozhFi9akWYGRNgIzpP4SqwtL0nIAoL3dJ-" +
        "n1-lRxUiIar_eGRVKd2NldSX7URaFxF2N_SfdD-AAYXUVCfm41yJ2A5awn1TzFXM" +
        "Efd7Evh2sm_8WsTSSYMjRvveXiZ4QiTocr80OYdNLIyuIc_kr20gaH3grhkWbT1P" +
        "Kws7IMBENPI_rQ2SlMUHu6EmIaXKwbqDlJpGHEB5ptmgMNeusuJVc9QGz8ql2lxV" +
        "DLXxgSg1Lk3E27F1EHfZ9fqRaa0dgqO6Z1zsCTPGeOnEKqgXY3nK4j_EkDIvaCiT" +
        "uQV3GfFdPAQL16wgcMCMpQ",
    "qi":
        "IhGkfNP6B13GhT-2foFaKCm8mOfm8UFSnWmAumC2t_-hzRej015_msvMMnPBLj1W" +
        "yOt8XNcg6BTfKkwxNjnAyH80rZKLk3c7pSJxAKWcxgDMqHMM0inN1NqWRrGdJ1qc" +
        "zZoOK2Lf3jkKp073Dx3FSJtvkYpHDhAtRsgznZ5hPgP8jJE9srxrAbkKJUqefpLY" +
        "WaBNHWIrOgp_e1hIg2EaCd5vGs2LSe9ImYdohpTxjT_Cm7AntWB_2t3BwGBKZk4V" +
        "8Tb2YjBm_rCr_dzyGXfaWw_dmt8xus5jIFydidMIf27aa0_mZ6uXyY6Ub5hHXmrC" +
        "icradD9-6-uHqa_ODhXAKQ",
    "kid": "2011-04-29"
})

if __name__ == '__main__':
    test_serialize_unsigned()
    test_ans104_verification()
    test_ans102_verification()
