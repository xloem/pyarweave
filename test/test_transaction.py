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


from ar import Peer, Transaction
import pytest


def test_transaction_reserialization():
    txbytes = (
        b'\x00\x057\x02\xb1/X3\x8a,\xcbD\xa8\xee\xdd\x1ajF\x07\xd7\xca2c?V' +
        b'#`8\xf1\x0b\xc1`1\x03\x98\xbc0\x923T#\x0b\xc8\xf4Yh\xeej\xfd*NAe' +
        b'\x9cP\xc0\xa7u\x84rZp+W\xb3\xa8\xfb/\xb0\xc8\xf6*\xfb\x8d\xf4M[' +
        b'\xb7\x98n\xe8\xaaQ\xe3\x88\x02\x00\xe5\xb0\xae\x97c\xc9S\x18p' +
        b'\xde{\x97q\xd7>.$\xc4\x7f\xfa\xe8zT\x84\xbf\xbf\xca\xd5\xe5\x0fU' +
        b'X\x10\xa1\xbe\x15X)A\xd4\xfa\xf1\xb0\xf1~1!\xab\x7f\x9eG\x90\xe3' +
        b'\x1bjS\x86\x01\t\xf3\xd6Y\x9a\xce\xd7\xa8w\xb1\xec\xc6z\x94u\xd0' +
        b'\x9c\x1e\xd4y\x87\xe52\xd1+\xf6\x9fB\x01eiGU\xa1W\xbd\x9bQ@q^d' +
        b'\x19\xc2\xa5Gr9*\xe9\xc0\xea\x08\xeb\x91|:\xc3\xc5\x1d\x01\xae2O' +
        b'\x051d\x90\xffak\xa2[\x1e\x8f=\xf2\xbc\xa8T\x9f\xa0R\x11]\xb2' +
        b'\x08\xb9-}0\xb1\xe73\xad\x07\x7fq\x18EEt\xff\xe0\xae\x8bS\xc2' +
        b'\xd0\xf1\x8c\x15gdG\xd1EC\xbbNw\xcb\x0e8\x97\x98\x11\x11\x88\xda' +
        b'\xa4\xe2l\x1d\xba\x00\xf8\x07+\xdb4\xe29m\xdcM|T4G\xce\xc4g\xa5' +
        b'\xfa\xd0vw\xee\x1d&\x12\x05\x9a`\x02a\xd9)\xf4\x15q\xe3\xe4\xb3' +
        b'\xfe\xe1p%\xe5\xc0\x89v\xda\x03\x13\xf3\xc4\tU\xcd\x89u\xb3\xdc=' +
        b'\xe0\xf4e\xfb7\x04\xf4(\'\x14B\x9cPl7\x1cp\x05\xbc&\x7f\xd7\xba' +
        b'\x98\xe3\xc8V\xd1\xc9\xa5\x86S\x9b4\x12\x97\xf0\x01\x91\xa1vo' +
        b'\xe1\x9e\xf5:3*;m\xff&\xdd\x7f\xd7\xbc\xec\x84\xa7(L\xe4\xf77' +
        b'\x89^K\xef\xe16\x93\xd3Q\x92\xcce\\\xbd\xdb}\x88\x19\xd6\xc4\x89' +
        b'\xed\xd4\x8f\x00\xc5\xd6$\x1b]\xf0g_\x8a8\xed\x06\x8f\x98\x9a' +
        b'\x98\xbc\xba!p\xd1\x89\xdd\xd7h\xafk\xfe\xd4:\xdb6\xfe0\xaf\xfc' +
        b'\x9d\xe1\x12BE\x9d>T!\x1d\xca\xbb\x8a\xb3#\x83\x1f6\xd4\x81B\xe0' +
        b'\xf5\xd1\xc4[\x08\xb0:\xafjVEV\xa1\xb4QD)ww\x94\xc5U\x1d\x1d\xd1' +
        b'\x9a\xb2\xc2^\xba\x90\xb3\x93.\x0f\x0f\xa78\xca\xf3\r\xd1\xc9B|' +
        b'\xb0,\xe6q\xb7X\xe0\x1b\x132\xc8G\xfd\x1f#[\xea\xb1\xb1gN\xe6' +
        b'\xba\x0c\x82%c\xa5\xe6\\?\xda\xbd\xbe\xcd\x9c\xec\xc7\xb6\xccp' +
        b'\x84\xec\xf0\xa7\x05\xa5\xc4P\xc8\x93\xa2\x08\x0c\x91u\xc2\xccw' +
        b'\x0f\x19\xfc\x94?\xee\xa3 \xc7\xf9\x18\xaa\rBl\x80\xa7=\xc1\xa4Q' +
        b'U\xb5\x00p\xab\x82\xae\xed\xba_\x8b\xe4H$\x7f\xd5mB\x04\x05\x015' +
        b'\xf9\x04&\x00\x04\x08[\x01\x0f \xeb\\\\W\x98\xa0fgwl\x9e\xc5\xf0' +
        b'Q\xb2u\xac>C\xbd=p\xd8\x84PT\xde\xa5&\xcd\xa1\xc3\x02\x00\x9f' +
        b'\x0bJ\xb3\xa1\xe91\xca\xf2\x0e+#\x0b\x1b\r\x8a\xb8\xa6_+\x05U9' +
        b'\xc5Y\x96\x01\xda\x1b\xb4Xq\x88m\xa3\xd0\xaf \xa2\x84\xe2H{\x81S' +
        b'\xa9L\xc6w\xb6\xf6 \xccq7O\xd0\xe1\xff\xa7\xd0.W\xcb\xb5^\xb3' +
        b'\xa9\xd3\x16\x06<\x0b\xb3\x1b-)%\x88\x87\xd9N&B\xcc\x05\x89\xf0' +
        b'\x97\xc9\xd8r\xf9\xe5\xf5\xe4S\xe9\xc8\xd2\xa4B\\P\x88\xa0y^Qf' +
        b'\xf9\xea\xa7(\x9d\xd6Fb\x1a\xe1)\r\xc2\'&\n\r\x92\x17\x88K\xd9' +
        b'\xe6\xd9\xfeV\x12\xf2\xfey\xef\x89K;\x8b\xf3\xa5\x17\x0b\xddW' +
        b'\x1b\\$\xb4\x9bh\xa9\xa1\xf2\xe3,t\xeb\xc5xm\xc9n\xdbg6\xe1\xe8Q' +
        b'v\xf1\xb9\n\xf9<M\x93\xebyl\xad\xc4O\x08\xc5\x9b\x133\x1d\xe5' +
        b'\xc5X\xca\x9eM.\xc9\xd2z\x8d\x8a\xfe,\xd1\xf3)\x81\x19\x04\xc7' +
        b'\x05q\xffB\r458\x12\x12\x7f\xe6\x12>\xd2<\xaa\x9d}\x9d\xaf/\xcfS' +
        b'\x08\x00@\x0e\xe6\x10\x01\xaf\xfb\x12p\x0c\xa5\xa1\xc3\x9c&\xae' +
        b'\xb4Pr\xde\xd3\x0eo\x1c\xc9\x90\x9d\x84#i\x9dv\xcd7\x16o\x19P' +
        b'\xaa$)\x1a\xab\x99\x9cl=\xda\x18H\xd7\xa23Y\x17\xa9)\xf1\xc1O' +
        b'\xf1\xfe@\x88Ud\x9a\x16\x90t\xa6\xeaHbL\xb1F&\xe1|t\xf4\x989\xe9' +
        b'\xbb\x93i\xeec\xec*N\x85\x9a1H2\xce\x8b\xb8c\xf9^\xca\xef\xd7' +
        b'\xb5o\xd31(\xd8-\xccT\x9c\xfc\x10r\xe1\x8a\xa5!\xf7\x89\xd5&ZY' +
        b'\xf7*\x89\x15<\x0be\xc2J\xcbu\x81\x0c\xe2e\x95\x1e\x0c\xccD\x01q' +
        b'\xbd~(\x1f\x1d\xde\x1a\xf2Ye\xba2\xb6\xaa7\xc2\xa1\xd6\x1e\x02w' +
        b'\xb6\x92\xc9\xae\x1b\xb3\xdd92\x94\xb6\xa6\xf5m\xc9a\xe7\xd2\xc4' +
        b'\x86\xba\xcd4\x87}\xbbZ\x8cO\xa2+\xfc\xf1\xf8\xa8\xd5\x94\xf6' +
        b'\xf6\x99\xe9=\xbe\ro\xba\xce\xc5\xb1\xb6Z\'\xcc*_\x05\xa5\x0c' +
        b'\xcf\xd99\xaa\xf6\xdcQ\xec\x9c{\x06V6\xd3\x81)\xc6\xb7\t?l\xac h' +
        b'u\xaf\xec\x1fz\x17\x8e%\xf3\xec\xde\xaeC\x1a\x05\x05\x08\x12|' +
        b'\x1b\xa8\x00\x00\x00\x00\x06\x00\x08\x00\x0bTip-Typedata upload' +
        b'\x00\t\x00\nUnix-Time1657125755\x00\x0b\x00\x06App-Version1.23.0' +
        b'\x00\x08\x00\x0bApp-NameArDrive-Web\x00\x0e\x00\x05Bundle-Versio' +
        b'n2.0.0\x00\r\x00\x06Bundle-Formatbinary'
    )
    txjson = {
        'data': '',
        'id': 'sS9YM4osy0So7t0aakYH18oyYz9WI2A48QvBYDEDmLw',
        'last_tx': 'kjNUIwvI9Flo7mr9Kk5BZZxQwKd1hHJacCtXs6j7L7DI9ir7jfRNW7eYbuiqUeOI',
        'owner': '5bCul2PJUxhw3nuXcdc-LiTEf_roelSEv7_K1eUPVVgQob4VWClB1PrxsPF-MSGrf55HkOMbalOGAQnz1lmazteod7HsxnqUddCcHtR5h-Uy0Sv2n0IBZWlHVaFXvZtRQHFeZBnCpUdyOSrpwOoI65F8OsPFHQGuMk8FMWSQ_2Frolsejz3yvKhUn6BSEV2yCLktfTCx5zOtB39xGEVFdP_grotTwtDxjBVnZEfRRUO7TnfLDjiXmBERiNqk4mwdugD4ByvbNOI5bdxNfFQ0R87EZ6X60HZ37h0mEgWaYAJh2Sn0FXHj5LP-4XAl5cCJdtoDE_PECVXNiXWz3D3g9GX7NwT0KCcUQpxQbDcccAW8Jn_XupjjyFbRyaWGU5s0EpfwAZGhdm_hnvU6Myo7bf8m3X_XvOyEpyhM5Pc3iV5L7-E2k9NRksxlXL3bfYgZ1sSJ7dSPAMXWJBtd8GdfijjtBo-Ympi8uiFw0Ynd12iva_7UOts2_jCv_J3hEkJFnT5UIR3Ku4qzI4MfNtSBQuD10cRbCLA6r2pWRVahtFFEKXd3lMVVHR3RmrLCXrqQs5MuDw-nOMrzDdHJQnywLOZxt1jgGxMyyEf9HyNb6rGxZ07mugyCJWOl5lw_2r2-zZzsx7bMcITs8KcFpcRQyJOiCAyRdcLMdw8Z_JQ_7qM',
        'quantity': '5200479270',
        'reward': '34669861800',
        'signature': 'nwtKs6HpMcryDisjCxsNirimXysFVTnFWZYB2hu0WHGIbaPQryCihOJIe4FTqUzGd7b2IMxxN0_Q4f-n0C5Xy7Ves6nTFgY8C7MbLSkliIfZTiZCzAWJ8JfJ2HL55fXkU-nI0qRCXFCIoHleUWb56qcondZGYhrhKQ3CJyYKDZIXiEvZ5tn-VhLy_nnviUs7i_OlFwvdVxtcJLSbaKmh8uMsdOvFeG3JbttnNuHoUXbxuQr5PE2T63lsrcRPCMWbEzMd5cVYyp5NLsnSeo2K_izR8ymBGQTHBXH_Qg00NTgSEn_mEj7SPKqdfZ2vL89TCABADuYQAa_7EnAMpaHDnCautFBy3tMObxzJkJ2EI2mdds03Fm8ZUKokKRqrmZxsPdoYSNeiM1kXqSnxwU_x_kCIVWSaFpB0pupIYkyxRibhfHT0mDnpu5Np7mPsKk6FmjFIMs6LuGP5Xsrv17Vv0zEo2C3MVJz8EHLhiqUh94nVJlpZ9yqJFTwLZcJKy3WBDOJllR4MzEQBcb1-KB8d3hryWWW6MraqN8Kh1h4Cd7aSya4bs905MpS2pvVtyWHn0sSGus00h327WoxPoiv88fio1ZT29pnpPb4Nb7rOxbG2WifMKl8FpQzP2Tmq9txR7Jx7BlY204EpxrcJP2ysIGh1r-wfeheOJfPs3q5DGgU',
        'tags': [
            {'name': 'VGlwLVR5cGU', 'value': 'ZGF0YSB1cGxvYWQ'},
            {'name': 'VW5peC1UaW1l', 'value': 'MTY1NzEyNTc1NQ'},
            {'name': 'QXBwLVZlcnNpb24', 'value': 'MS4yMy4w'},
            {'name': 'QXBwLU5hbWU', 'value': 'QXJEcml2ZS1XZWI'},
            {'name': 'QnVuZGxlLVZlcnNpb24', 'value': 'Mi4wLjA'},
            {'name': 'QnVuZGxlLUZvcm1hdA', 'value': 'YmluYXJ5'}
        ],
        'target': 'x_kYqg1CbICnPcGkUVW1AHCrgq7tul-L5Egkf9VtQgQ',
        'format': 2,
        'data_root': '61xcV5igZmd3bJ7F8FGydaw-Q709cNiEUFTepSbNocM',
        'data_size': '140181775',
        'data_tree': []
    }

    tx = Transaction.frombytes(txbytes)
    assert tx.to_dict() == txjson
    tx.load(txjson)
    assert tx.tobytes() == txbytes

if __name__ == '__main__':
    test_transaction_reserialization()
