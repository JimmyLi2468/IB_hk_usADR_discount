import asyncio
import PyQt5.QtWidgets as qt
# import PySide6.QtWidgets as qt

from ib_insync import IB, util
from ib_insync.contract import *  # noqa
class TickerTable(qt.QTableWidget):

    headers = [
        'symbol', 'market','bid','ask', 
        'last', 'close',
        'high','low',
        'discount'
    ]
    #    'rtHistVolatility','histVolatility','impliedVolatility',
    #    'callOpenInterest','putOpenInterest','callVolume','putVolume']

    # pair hk ticker and us ticker to a pair name
    # pair name is us ticker
    # HK ticker: pair name(us ticker)
    # US ticker: pair name(us ticker)
    easypair = {
        '700': 'TCEHY',
#        'fu':'TCEHY',
        '9988': 'BABA',
        'TCEHY':'TCEHY',
        'BABA': 'BABA',
        '9999':'NTES',
        'NTES':'NTES',
        '9698':'GDS',
        'GDS':'GDS',
        '1833':'PIAHY',
        'PIAHY':'PIAHY',
        '9888':'BIDU',
        'BIDU':'BIDU',
        '1810':'XIACY',
        'XIACY':'XIACY',
        'JD':'JD',
        '9618':'JD',
        'ASMVY':'ASMVY',
        '522':'ASMVY',
        'LNVGY':'LNVGY',
        '992':'LNVGY'
    }
    # HK to US stock ratio
    ratio = {
        'TCEHY':1,
        'BABA': 8,
        'NTES':5,
        'GDS':8,
        'PIAHY':2,
        'BIDU':8,
        'XIACY':5,
        'JD':2,
        'ASMVY':3,
        'LNVGY':20
    }
    
    

    def __init__(self, parent=None):
        qt.QTableWidget.__init__(self, parent)
        self.conId2Row = {}
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        self.setAlternatingRowColors(True)
        # easydata is a dictionary
        # there are two types of entries:
        # 1: ForEx : market rate
        # 2: stock pairs: hkstock: market or close
        #                 usstock: market or close
        self.easydata = {}
        # discount rate for each pair of stocks
        self.pairdiscount = {}
        self.forex = 0.0
        
    def __contains__(self, contract):
        assert contract.conId
        return contract.conId in self.conId2Row

    def addTicker(self, ticker):
        row = self.rowCount()
        self.insertRow(row)
        self.conId2Row[ticker.contract.conId] = row
        for col in range(len(self.headers)):
            item = qt.QTableWidgetItem('-')
            self.setItem(row, col, item)
        item = self.item(row, 0)
        item.setText(ticker.contract.symbol + (
            ticker.contract.currency if ticker.contract.secType == 'CASH'
            else ''))
        self.resizeColumnsToContents()
        
        
        

    def clearTickers(self):
        self.setRowCount(0)
        self.conId2Row.clear()

    def onPendingTickers(self, tickers):
        # for each ticker
        # find out if it's a ForEx rate or stock
        # store information to the key
        for ticker in tickers:
            # stock: STK, Forex pair: CASH, Option: OPT, Future: FUT
            
            # The ticker is a ForEX
            # store market rate to the symbol
            if ticker.contract.secType == 'CASH':
                # **** using localSymbol because symbol is wrong ****
                self.easydata[ticker.contract.localSymbol] = (ticker.bid+ticker.ask)/2
            # The ticker is a stocker
            if ticker.contract.secType == 'STK':
                
                sym = ticker.contract.symbol
                #print(sym)
                # operate only if there's a pair defined in easypair
                if sym in self.easypair:
                    # get pair name
                    pairname = self.easypair[sym]
                    #print('pairname: '+pairname)
                    # if pair name not in easydata, initialize it in easydata 
                    if pairname not in self.easydata:
                        self.easydata[pairname] = {}
                    # if there's market value, find market price
                    # else use close price
                    # note: it's possible both values are missing
                    if ticker.bid > 0 and ticker.ask > 0:
                        self.easydata[pairname][sym] = (ticker.bid+ticker.ask)/2
                    elif ticker.close > 0:
                        self.easydata[pairname][sym] = ticker.close
                    
        # end for loop for processing easydata 
        #print(self.easydata)
        # initialize two variables: forex rate
        #                           stock pair ratio
        ratio = 0
        # process each pair in easydata
        # and add to pairdiscount
        for pair in self.easydata:
            # if length of the string > 6, then it should be a forex rate
            # **** need to change this if there's other symbols longer than 6 ****
            if len(pair) > 6:
                if self.easydata[pair] != 0 and pair == 'USD.HKD':
                    self.forex = self.easydata[pair]
            # else it should be the stock pair
            elif len(self.easydata[pair]) >=2 :
                #print(self.easydata[pair])
                ratio = self.ratio[pair]
                hk = 0.0
                us = 0.0
                # loop through the stock pair
                for stk in self.easydata[pair]:
                    # process only if there is data
                    #if self.easydata[pair][stk] != 0:
                    # if the ticker is digits, then it's hk stock
                    # else it's us stock
                    if stk.isdigit():
                        hk = self.easydata[pair][stk]
                    else:
                        us = self.easydata[pair][stk]
                    # process only if all data != 0
                    if self.forex != 0 and hk!= 0 and us != 0:
                        hkinUSD = hk*ratio/self.forex
                        result = (hkinUSD - us)/hkinUSD
                        # this is just a debug message
                        '''
                        print(str(hk) + ' ' 
                              + str(self.forex) + ' ' 
                              + str(hkinUSD) + ' ' 
                              + str(us) + ' ' 
                              + str(result))
                        '''
                        # convert result to percentage
                        self.pairdiscount[pair] = result*100
      
        #if self.pairdiscount:
        #    print(self.pairdiscount)
        #    print('==================')
        
        # loop through each ticker and print to table
        for ticker in tickers:
            row = self.conId2Row[ticker.contract.conId]
            for col, header in enumerate(self.headers):
                if col == 0:
                    continue
                item = self.item(row, col)
                val = 'nan'
                
                # market rate is (bid+ask)/2
                # round the float to 4 decimal places
                if header == 'market' :
                    val = (ticker.bid + ticker.ask)/2
                    val = round(val,4)
                # get discount rate
                # process only if
                # 1. the ticker is a stock
                # 2. the ticker is a pair in easypair
                # 3. the ticker is the us ticker
                # 4. the ticker's discount is calculated
                elif header == 'discount':
                    if ticker.contract.secType == 'STK':
                        sym = ticker.contract.symbol
                        if sym in self.pairdiscount:
                            val = self.pairdiscount[sym]
                            val = round(val,4)
                # other labels can be obtained from ticker itself
                else:
                    val = getattr(ticker, header)
                
            
                item.setText(str(val))
class Window(qt.QWidget):

    def __init__(self, host, port, clientId):
        qt.QWidget.__init__(self)
        self.edit = qt.QLineEdit('', self)
        self.edit.editingFinished.connect(self.add)
        self.table = TickerTable()
        self.connectButton = qt.QPushButton('Connect')
        self.connectButton.clicked.connect(self.onConnectButtonClicked)
        layout = qt.QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(self.table)
        layout.addWidget(self.connectButton)
        #self.qwidget.setFont(QFont('Areial',14))

        self.connectInfo = (host, port, clientId)
        self.ib = IB()
        self.ib.pendingTickersEvent += self.table.onPendingTickers
        #self.layout.setFont(QFont('Areial',14))

    def add(self, text=''):
        text = text or self.edit.text()
        if text:
            contract = eval(text)
            if (contract and self.ib.qualifyContracts(contract)
                    and contract not in self.table):
                ticker = self.ib.reqMktData(contract, '', False, False, None)
                self.table.addTicker(ticker)
            self.edit.setText(text)

    def onConnectButtonClicked(self, _):
        if self.ib.isConnected():
            self.ib.disconnect()
            self.table.clearTickers()
            self.connectButton.setText('Connect')
        else:
            self.ib.connect(*self.connectInfo)
            self.ib.reqMarketDataType(2)
            self.connectButton.setText('Disonnect')
            for symbol in (
                    'EURUSD', 'USDJPY', 'USDHKD'):
                self.add(f"Forex('{symbol}')")
            for symbol in (
                    '992','522','9618','700', '9988', '9888','9999','9698','1833','1810'):
                self.add(f"Stock('{symbol}','SEHK','HKD')")
            for symbol in (
                    'LNVGY','ASMVY','JD','BABA','TCEHY','XIACY','BIDU','PIAHY','GDS','NTES'):
                self.add(f"Stock('{symbol}','SMART','USD')")
            #for symbol in (
            #        '700', '9988', '9888'):
            #    self.add(f"Stock('{symbol}','SEHK','HKD')")
            self.add("Stock('TSLA', 'SMART', 'USD')")

    def closeEvent(self, ev):
        asyncio.get_event_loop().stop()
		
if __name__ == '__main__':
    util.patchAsyncio()
    util.useQt()
    # util.useQt('PySide6')
    window = Window('127.0.0.1', 7497, 1)
    window.resize(600, 600)
    window.show()
    IB.run()



