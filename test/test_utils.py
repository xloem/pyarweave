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

from ar.utils import winston_to_ar, ar_to_winston


def test_winston_to_ar():
    fee = {
        'winston': '938884',
        'ar': '0.000000938884'
    }

    ar = winston_to_ar(fee['winston'])
    assert ar == float(fee['ar'])


def test_ar_to_winston():
    fee = {
        'winston': '938884',
        'ar': '0.000000938884'
    }

    winston = ar_to_winston(fee['ar'])

    assert winston == fee['winston']


if __name__ == '__main__':
    test_ar_to_winston()
    test_winston_to_ar()
