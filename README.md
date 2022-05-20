# PyArweave
This is a small python client for arweave, based on https://github.com/MikeHibbert/arweave-python-client .

I can struggle to code, so the hope is to keep this small and simple and ask the universe for more developers to take over maintainership.

Meanwhile, here's an arweave library.

## Installing
```
pip install pyarweave
```

# possibly-outdated documentation

## Using your wallet
Once installed you can import it and supply the wallet object with the path to your wallet JSON file:
```
import ar


wallet_file_path = '/some/folder/on/your/system'
wallet = ar.Wallet(wallet_file_path)

balance =  wallet.balance

last_transaction = wallet.get_last_transaction_id()
```

## Loading your wallet
If your wallet data is stored in a secret manager or anywhere other than a file, you can load it with the `from_data` classmethod:
```
import ar

wallet_data = // Load from cloud storage or wherever
wallet = ar.Wallet.from_data(wallet_data)

balance =  wallet.balance
```

## Transactions
To send a transaction you will need to open your wallet, create a transaction object, sign the transaction and then finally post the transaction:
```
import ar


wallet_file_path = '/some/folder/on/your/system'
wallet = ar.Wallet(wallet_file_path)

transaction = ar.Transaction(wallet, quantity=0.3, to='<some wallet address')
transaction.sign()
transaction.send()
```

#####ATTENTION! quantity is in AR and is automatically converted to Winston before sending

## Uploading large files
Uploading large data files is now possible! you can now upload data larger than your physical memory or maximum transaction size (12MB) in the following way
```
from ar.arweave_lib import Wallet, Transaction
from ar.transaction_uploader import get_uploader

wallet = Wallet(jwk_file)

with open('my_mahoosive_file.dat', 'rb', buffering=0) as file_handler:
    tx = Transaction(wallet, file_handler=file_handler, file_path='/some/path/my_mahoosive_file.dat')
    tx.add_tag('Content-Type', 'application/dat')
    tx.sign()

    uploader = get_uploader(tx, file_handler)

    while not uploader.is_complete:
        uploader.upload_chunk()

        logger.info('{}% complete, {}/{}'.format(
            uploader.pct_complete, uploader.uploaded_chunks, uploader.total_chunks
        ))
```
NOTE: When uploading you only need to supply a file handle with buffering=0 instead of reading in the data all at once. The data will be read progressively in small chunks

To check the status of a transaction after sending:
```
status = transaction.get_status()
```

To check the status much later you can store the ```transaction.id``` and reload it:
```
transaction = Transaction(wallet, id='some id you stored')
status = transaction.get_status()
```

## Storing data
As you know Arweave allows you to permanently store data on the network and you can do this by supplying data to the transaction as a string object:
```
wallet = Wallet(jwk_file)

with open('myfile.pdf', 'r') as mypdf:
    pdf_string_data = mypdf.read()

    transaction = Transaction(wallet, data=pdf_string_data)
    transaction.sign()
    transaction.send()
```

## Retrieving transactions/data
To get the information about a transaction you can create a transaction object with the ID of that transaction:
```
tx = Transaction(wallet, id=<your tx id>)
tx.get_transaction()
```

In addition you may want to get the data attached to this transaction once you've decided you need it:
```
tx.get_data()
print(tx.data)
> 'some data'
```

## Sending to a specific Node
You can specify a specific node by setting the api_url of the wallet/transaction object:
```
wallet = Wallet(jwk_file)
wallet.api_url = 'some specific node ip/address and port'

Or

transaction = Transaction(wallet, data=pdf_string_data)
transaction.api_url = 'some specific node ip/address and port'

```

## Arql
You can now perform searches using the arql method:
```
from ar.arweave_lib import arql

wallet_file_path = '/some/folder/on/your/system'
wallet = ar.Wallet(wallet_file_path)

transaction_ids = arql(
    wallet,
    {
        'op': 'equals',
        'expr1': 'from',
        'expr2': 'Some owner address'
    })
```

Alternatively, you can use a the helper method arql_with_transaction_data() to get all transaction ids as well as all the data stored in the blockchain
```
import ar

wallet_file_path = '/some/folder/on/your/system'
wallet = ar.Wallet(wallet_file_path)

transactions = aweave.arql_with_transaction_data(
    wallet,
    {
        'op': 'equals',
        'expr1': 'from',
        'expr2': 'Some owner address'
    })
```
