#=============================================================
# 2014-Sep-13 Sat 04:00 PM
# Intent: To read xlxs files and show stock in hand.
#
#=============================================================
from collections import defaultdict, OrderedDict


from Util.Misc import PrintInBox
from Util.Exception import MyException

from whopaid.bom import GetBOM
from whopaid.IncomingMaterial import GetAllSuppliersDict
from whopaid.UtilWhoPaid import GetAllCompaniesDict
from whopaid.SanityChecks import  CheckConsistency, SendAutomaticHeartBeat


def ShowStockInHandOnScreen():
  finalPartsUsedDict = defaultdict(int)#Change it from int to decimal or something else if there is an overflow error.
  bom = GetBOM()

  allBillsDict = GetAllCompaniesDict().GetAllBillsOfAllCompaniesAsDict()
  for comp, bills in allBillsDict.iteritems():
    for b in bills:
      usedPartsDict = bom.partsAndQtyForThisProductAsDict(b.materialDesc)
      for part, quantity in usedPartsDict.items():
        finalPartsUsedDict[part] -= quantity*b.materialQty

  allSupplierDict = GetAllSuppliersDict().GetAllBillsOfAllSuppliersAsDict()
  for comp, bills in allSupplierDict.iteritems():
    for b in bills:
      finalPartsUsedDict[b.materialDesc] += b.materialQty

  PrintInBox("Stock in hand")
  finalPartsUsedDict = OrderedDict(sorted(finalPartsUsedDict.items()))
  for parts, qty in finalPartsUsedDict.iteritems():
    print("{:<15}{:15}".format(parts, qty))


def main():
  try:
    CheckConsistency()
    ShowStockInHandOnScreen()
    #SendAutomaticHeartBeat()
  except MyException as ex:
    PrintInBox(str(ex))

if __name__ == "__main__":
  main()
