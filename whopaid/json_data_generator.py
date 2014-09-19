
from Util.Config import GetOption
from Util.Misc import DD_MM_YYYY, DD_MMM_YYYY

from whopaid.customers_info import GetAllCustomersInfo
from whopaid.util_whopaid import SelectUnpaidBillsFrom,\
    GetAllCompaniesDict, datex, RemoveTrackingBills
from whopaid.util_formc import QuarterlyClubbedFORMC

import datetime
import json
import os

UBEROBSERVERDIR = os.getenv("UBEROBSERVERDIR")
PUSH_FILE       = os.path.join(UBEROBSERVERDIR, "utils", "push.py")
DUMPING_DIR     = os.path.join(UBEROBSERVERDIR, "static", "dbs")
SMALL_NAME      = GetOption("CONFIG_SECTION", "SmallName")

EXT = ".json"
PMT_JSON_FILE_NAME   = os.path.abspath(os.path.join(DUMPING_DIR, "PMT_" + SMALL_NAME + EXT))
ORDER_JSON_FILE_NAME = os.path.abspath(os.path.join(DUMPING_DIR, "ORDER_" + SMALL_NAME + EXT))
FORMC_JSON_FILE_NAME = os.path.abspath(os.path.join(DUMPING_DIR, "FORMC_" + SMALL_NAME + EXT))
RAW_MATERIAL_JSON_FILE_NAME = os.path.abspath(os.path.join(DUMPING_DIR, "RAWMAT_" + SMALL_NAME + EXT))
FINISHED_STOCK_IN_HAND_JSON_FILE_NAME = os.path.abspath(os.path.join(DUMPING_DIR, "FINSTOCK_" + SMALL_NAME + EXT))

ALL_COMPANIES_DICT = GetAllCompaniesDict()
"""
OrderDB:
data =
[
// Each {} is an object in a list and represents a collection of orders on
// particular date
    {
        date: "21-Apr-2014",
        orders:[
          {
            "custName":"AWT",
            "md":"15x13x.77=30pc; .83=20pc; .90=20pc; PO#AWT/14-15/",
            "oNum":"AWT/14-15/0026"
          },
          {
            "custName":"MWW",
            "md":"13x10x.765=100pc; .96=35",
            "oNum":"PUR-27/14"
          }
        ],
    },
    {
        date: "22-Apr-2014",
        orders:[
          {
            "custName":"AWT",
            "md":"15x13x.77=30pc; .83=20pc; .90=20pc; PO#AWT/14-15/",
            "oNum":"AWT/14-15/0026"
          },
          {
            "custName":"MWW",
            "md":"13x10x.765=100pc; .96=35",
            "oNum":"PUR-27/14"
          }
        ]
        }
  }
]
"""


def _DumpOrdersDB():
  allOrdersDict = ALL_COMPANIES_DICT.GetAllOrdersOfAllCompaniesAsDict()

  if os.path.exists(ORDER_JSON_FILE_NAME):
    os.remove(ORDER_JSON_FILE_NAME)

  data = list()  # This will have one day orders

  for eachCompName, orders in allOrdersDict.iteritems():
    for eachOrder in orders:
      singleOrder = dict()
      singleOrder["custName"] = eachOrder.compName
      singleOrder["md"] = eachOrder.materialDesc
      singleOrder["oNum"] = eachOrder.orderNumber
      singleOrder["oDate"] = DD_MM_YYYY(eachOrder.orderDate)
      data.append(singleOrder)  # Just dump this single order there
                                # and we will club them date wise while
                                # generating final json

  with open(ORDER_JSON_FILE_NAME, "w+") as f:
    json.dump(data, f, separators=(',', ':'), indent=2)
  return

"""
RAWMAT_DB
data =
{
 parts:[
 {
 name: xyz,
 nowQty: 10
 reference: 20
 diff: -10
 },
 name: pqr,
 nowQty: 15
 reference: 10
 diff: 5
 {
 },
 ]
showVerbatimOnTop:
}
"""
def _DumpRawMaterialsNow():
  if os.path.exists(RAW_MATERIAL_JSON_FILE_NAME):
    os.remove(RAW_MATERIAL_JSON_FILE_NAME)

  from collections import OrderedDict
  from whopaid.stock_in_hand import CalculateRawMaterialSIH
  from whopaid.bom import GetReferenceLevelQtyForPart
  finalPartsUsedDict = CalculateRawMaterialSIH()
  finalPartsUsedDict = OrderedDict(sorted(finalPartsUsedDict.items()))


  data = dict()  # This will have one day orders
  parts = list()

  for part, qty in finalPartsUsedDict.iteritems():
    refLevel = GetReferenceLevelQtyForPart(part)
    singlePart=dict()
    singlePart["name"] = part
    singlePart["nowQty"] = qty
    singlePart["refLevel"] = refLevel
    singlePart["diff"] = int(qty) - int(refLevel)
    parts.append(singlePart)  # Just dump this single part there

  data["parts"] = parts

  from whopaid.incoming_material import GetAllSuppliersDict
  allSupplierDict = GetAllSuppliersDict().GetAllBillsOfAllSuppliersAsDict()
  recentIncomingMaterialInvoiceDate = max([b.materialReceivingDate for comp, bills in allSupplierDict.iteritems() for b in bills])

  allBillsDict = ALL_COMPANIES_DICT.GetAllBillsOfAllCompaniesAsDict()
  recentOutgoingMaterialBillDate = max([b.invoiceDate for comp, bills in allBillsDict.iteritems() for b in bills])

  compSmallName = GetOption("CONFIG_SECTION", "SmallName")
  data["showVerbatimOnTop"] = [
      "{} last incoming invoice date: {}".format(compSmallName, DD_MM_YYYY(recentIncomingMaterialInvoiceDate)),
      "{} last outgoing invoice date: {}".format(compSmallName, DD_MM_YYYY(recentOutgoingMaterialBillDate)),
      ]

  with open(RAW_MATERIAL_JSON_FILE_NAME, "w+") as f:
    json.dump(data, f, separators=(',', ':'), indent=2)
  return

def _DumpFinStockInHand():
  if os.path.exists(FINISHED_STOCK_IN_HAND_JSON_FILE_NAME):
    os.remove(FINISHED_STOCK_IN_HAND_JSON_FILE_NAME)

  from collections import OrderedDict
  from whopaid.stock_in_hand import CalculateFinishedGoodsSIH
  finalFinishedGoodsDict = CalculateFinishedGoodsSIH()
  finalFinishedGoodsDict = OrderedDict(sorted(finalFinishedGoodsDict.items()))


  data = dict()  # This will have one day orders
  models = list()

  for model, qty in finalFinishedGoodsDict.iteritems():
    singleModel=dict()
    singleModel["name"] = model
    singleModel["nowQty"] = qty
    models.append(singleModel)  # Just dump this single part there

  data["models"] = models

  from whopaid.daily_production import GetDailyProductionDict
  allProd = GetDailyProductionDict().GetDailyProdOfAllMaterialsAsDict()
  recentDailyProdcutionDate = max([b.productionDate for product, dpRows in allProd.iteritems() for b in dpRows])

  allBillsDict = ALL_COMPANIES_DICT.GetAllBillsOfAllCompaniesAsDict()
  recentOutgoingMaterialBillDate = max([b.invoiceDate for comp, bills in allBillsDict.iteritems() for b in bills])

  compSmallName = GetOption("CONFIG_SECTION", "SmallName")
  data["showVerbatimOnTop"] = [
      "{} last material produced on : {}".format(compSmallName, DD_MM_YYYY(recentDailyProdcutionDate)),
      "{} last outgoing invoice date: {}".format(compSmallName, DD_MM_YYYY(recentOutgoingMaterialBillDate)),
      ]

  with open(FINISHED_STOCK_IN_HAND_JSON_FILE_NAME, "w+") as f:
    json.dump(data, f, separators=(',', ':'), indent=2)
  return

"""
paymentDB
data=
{
    customers:[
    {
        name:"Starbucks | SDAT",
        trust: .5,
        bills:[
            { bn:"1", bd:"1-Mar-14", ba:"1400"},
            { bn:"2", bd:"2-Mar-14", ba:"2400"},
            ],
        trust: .5,
    },
    {
        name:"CostaCoffee | Omega",
        trust: .5,
        bills:[
            { bn:"3", bd:"3-Mar-14", ba:"3400"},
            { bn:"4", bd:"4-Mar-14", ba:"4400"},
            ],
    }
    ]
}

"""


def _DumpPaymentsDB():
  allBillsDict = ALL_COMPANIES_DICT.GetAllBillsOfAllCompaniesAsDict()
  allAdjustmentsDict = ALL_COMPANIES_DICT.GetAllAdjustmentsOfAllCompaniesAsDict()
  allCustInfo = GetAllCustomersInfo()

  if os.path.exists(PMT_JSON_FILE_NAME):
    os.remove(PMT_JSON_FILE_NAME)

  data = {}
  allCustomers = []

  for eachCompName, eachCompBills in allBillsDict.iteritems():
    adjustmentList = allAdjustmentsDict.get(eachCompName, [])
    unpaidBillList = SelectUnpaidBillsFrom(eachCompBills)
    unpaidBillList = RemoveTrackingBills(unpaidBillList)
    oneCustomer = dict()
    oneCustomer["name"] = " {} | {}".format(eachCompName, SMALL_NAME)

    oneCustomerBills = []
    unpaidBillList = sorted(unpaidBillList, key=lambda b: datex(b.invoiceDate))
    for b in unpaidBillList:
      oneBill = {
          "bn": b.billNumber,
          "bd": DD_MM_YYYY(datex(b.invoiceDate)),
          "cd": str(b.daysOfCredit),
          "ba": str(int(b.amount))
          }
      oneCustomerBills.append(oneBill)

    for a in adjustmentList:
      if a.adjustmentAccountedFor:
        continue
      oneAdjustment = {
          "bn": a.adjustmentNo or "-1",
          "bd": DD_MM_YYYY(datex(a.invoiceDate)),
          "cd": "0",
          "ba": str(int(a.amount))
          }
      oneCustomerBills.append(oneAdjustment)  # For all practical purposes, an adjustment is treated as a bill with bill#-1

    oneCustomer["bills"] = oneCustomerBills
    oneCustomer["trust"] = allCustInfo.GetTrustForCustomer(eachCompName)

    if len(oneCustomerBills) > 0:
      allCustomers.append(oneCustomer)

  data["customers"] = allCustomers
  recentPmtDate = datetime.date.today() #TODO: Seems buggy fix it later and calculate real date.
  compSmallName = GetOption("CONFIG_SECTION", "SmallName")
  data["showVerbatimOnTop"] = "{} last pmt: {}".format(compSmallName, DD_MM_YYYY(recentPmtDate))

  with open(PMT_JSON_FILE_NAME, "w+") as f:
    json.dump(data, f, separators=(',', ':'), indent=2)
  return


def _DumpFormCData():
  allBillsDict = ALL_COMPANIES_DICT.GetAllBillsOfAllCompaniesAsDict()

  lastFormCEnteredOnDate = datetime.date(datetime.date.today().year-100, 1, 1)  # Choose a really low date
  for eachComp, billList in allBillsDict.iteritems():
    t = [b.formCReceivingDate for b in billList if b.formCReceivingDate and isinstance(b.formCReceivingDate, datetime.date)]
    if t:
      lastFormCEnteredOnDate = max(lastFormCEnteredOnDate, max(t))

  from copy import deepcopy
  formCReceivableDict = deepcopy(allBillsDict)
  for eachComp, billList in formCReceivableDict.items():
    newList = [b for b in billList if not b.formCReceivingDate and b.billingCategory.lower() in ["central"]]  # Inplace removal of bills
    if newList:
      formCReceivableDict[eachComp] = [b for b in billList if not b.formCReceivingDate and b.billingCategory.lower() in ["central"]]  # Inplace removal of bills
    else:
      del formCReceivableDict[eachComp]

  superSmallName = GetOption("CONFIG_SECTION", "SuperSmallName")

  def BillNoDateAmountDict(bill):
    singleBill = dict()
    singleBill["billNumber"] = int(bill.billNumber)
    singleBill["invoiceDateAsText"] = DD_MMM_YYYY(bill.invoiceDate)
    singleBill["invoiceDateIsoFormat"] = bill.invoiceDate.isoformat()
    singleBill["amount"] = str(int(bill.amount))
    return singleBill

  data = dict()
  allCompsFormC = list()
  for eachComp, billList in formCReceivableDict.iteritems():
    key = "{} | {}".format(eachComp, superSmallName)
    yd = QuarterlyClubbedFORMC(billList).GetYearDict()
    """
    year(dict)
     |--quarter(dict)
         |--bills(list)
    """
    for eachYear, quarters in yd.iteritems():
      for eachQuarter, billList in quarters.iteritems():
        quarters[eachQuarter] = [BillNoDateAmountDict(bill) for bill in billList]  # In place replacement of billList with smaller objcets containing only necessary data.
    singleCompFormC = {
        "key": key,
        "yd": yd,
                      }

    allCompsFormC.append(singleCompFormC)

  data["allCompsFormC"] = allCompsFormC
  compSmallName = GetOption("CONFIG_SECTION", "SmallName")
  data["showVerbatimOnTop"] = "{} : {}".format(compSmallName, DD_MM_YYYY(lastFormCEnteredOnDate))

  with open(FORMC_JSON_FILE_NAME, "w+") as f:
    json.dump(data, f, separators=(',', ':'), indent=2)
  return
  return


def _DumpJSONDB():
  _DumpFinStockInHand()
  _DumpRawMaterialsNow()
  _DumpFormCData()
  _DumpPaymentsDB()
  _DumpOrdersDB()
  return


def AskUberObserverToUploadJsons():
  #TODO:There is an extremely tight coupling within pmtapp and jsongenerator. For ex jsongenerator has to know the path of pushfile to execute it. Need a more elegant way to invoke uploads.
  import subprocess
  import Util
  Util.Misc.PrintInBox(PUSH_FILE)
  if not os.path.exists(PUSH_FILE):
    raise Exception("{} does not exist".format(PUSH_FILE))
  e = 'moc.liamg@ztigihba'
  v = 'live'
  cmd = "python \"{pushFile}\" --email={e} --version={v} --oauth2".format(pushFile=PUSH_FILE, e=e[::-1], v=v)
  print("Running: {}".format(cmd))
  subprocess.check_call(cmd, shell=True)
  return


def ParseOptions():
  import argparse
  parser = argparse.ArgumentParser()

  parser.add_argument("-gj", "--generate-json",
        dest='generateJson', action="store_true",
        default=False, help="If present, only then json data will be generated.")

  return parser.parse_args()

if __name__ == "__main__":
  args = ParseOptions()
  if args.generateJson:
    _DumpJSONDB()
