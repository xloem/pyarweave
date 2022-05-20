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

from flask import Flask, request
import logging
import json

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/tx', methods=['POST'])
def index():
    return 'OK'


@app.route('/chunk', methods=['POST'])
def chunk():
    if request.method == 'POST':
        logger.error(json.dumps(str(request.data)))
    return 'OK'


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1')
