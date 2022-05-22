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


from bundlr import DataItem
from ar import Wallet
import pytest

import sys
from jose.utils import base64url_decode

def test_serialize_unsigned():
    dataitem = DataItem(owner = wallet.raw_owner, anchor = b'00000000000000000000000000000000', tags = {'name':'value'}, data = b'Hello, world.')
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

    dataitem.sign(wallet.jwk_data)
    dataitem = DataItem.frombytes(dataitem.tobytes())
    assert dataitem.verify()

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
