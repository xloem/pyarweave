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

import json
from .peer import Peer

from . import DEFAULT_API_URL

TRANSACTION_DATA_LIMIT_IN_BYTES = 2000000

def arql(wallet, query):
    '''
    Creat your query like so:
    query = {
        'op': 'and',
          'expr1': {
            'op': 'equals',
            'expr1': 'from',
            'expr2': 'hnRI7JoN2vpv__w90o4MC_ybE9fse6SUemwQeY8hFxM'
          },
          'expr2': {
            'op': 'or',
            'expr1': {
              'op': 'equals',
              'expr1': 'type',
              'expr2': 'post'
            },
            'expr2': {
              'op': 'equals',
              'expr1': 'type',
              'expr2': 'comment'
            }
          }
    :param wallet:
    :param query:
    :return list of Transaction instances:
    '''

    return Peer(DEFAULT_API_URL).arql(query)


def arql_with_transaction_data(wallet, query):
    '''
    Creat your query like so:
    query = {
        'op': 'and',
          'expr1': {
            'op': 'equals',
            'expr1': 'from',
            'expr2': 'hnRI7JoN2vpv__w90o4MC_ybE9fse6SUemwQeY8hFxM'
          },
          'expr2': {
            'op': 'or',
            'expr1': {
              'op': 'equals',
              'expr1': 'type',
              'expr2': 'post'
            },
            'expr2': {
              'op': 'equals',
              'expr1': 'type',
              'expr2': 'comment'
            }
          }
    :param wallet:
    :param query:
    :return list of Transaction instances:
    '''

    transaction_ids = arql(wallet, query)
    if transaction_ids:
        transactions = []
        for transaction_id in transaction_ids:
            tx = Transaction(wallet, id=transaction_id)
            tx.get_transaction()
            tx.get_data()

            transactions.append(tx)

    return None
