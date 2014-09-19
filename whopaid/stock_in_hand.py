#=============================================================
# 2014-Sep-13 Sat 04:00 PM
# Intent: To read xlxs files and show stock in hand.
#
#=============================================================
from collections import defaultdict, OrderedDict

from Util.Exception import MyException
from Util.Misc import PrintInBox

from whopaid.bom import GetBOM
from whopaid.daily_production import GetDailyProductionDict
from whopaid.incoming_material import GetAllSuppliersDict
from whopaid.sanity_checks import CheckConsistency
from whopaid.util_whopaid import GetAllCompaniesDict


def CalculateRawMaterialSIH():
  finalPartsUsedDict = defaultdict(int)  # Change it from int to
  #decimal or something else if there is an overflow error.
  bom = GetBOM()

  #============================================================
  # Substract parts used for each model
  #============================================================

  dp = GetDailyProductionDict()
  allProd = dp.GetDailyProdOfAllMaterialsAsDict()
  for products, dpRows in allProd.iteritems():
    for row in dpRows:
      usedPartsDict = bom.partsAndQtyForThisProductAsDict(row.modelDesc)
      for part, quantity in usedPartsDict.items():
        finalPartsUsedDict[part] -= quantity * row.modelQty

  #============================================================
  # Add parts received from each supplier
  #============================================================
  allSupplierDict = GetAllSuppliersDict().GetAllBillsOfAllSuppliersAsDict()
  for comp, bills in allSupplierDict.iteritems():
    for b in bills:
      finalPartsUsedDict[b.materialDesc] += b.materialQty

  return finalPartsUsedDict

def CalculateFinishedGoodsSIH():
  finalFinishedGoodsDict = defaultdict(int)  # Change it from int to
  #decimal or something else if there is an overflow error.

  #============================================================
  # Add finished goods that have been produced in daliy production
  #============================================================

  dp = GetDailyProductionDict()
  allProd = dp.GetDailyProdOfAllMaterialsAsDict()
  for products, dpRows in allProd.iteritems():
    for row in dpRows:
      finalFinishedGoodsDict[row.modelDesc] += row.modelQty

  #============================================================
  # Substract finished goods that have been shipped
  #============================================================
  allBillsDict = GetAllCompaniesDict().GetAllBillsOfAllCompaniesAsDict()
  for comp, bills in allBillsDict.iteritems():
    for b in bills:
      finalFinishedGoodsDict[b.modelDesc] -= b.modelQty

  return finalFinishedGoodsDict


def ShowFinishedGoodsSIHOnScreen():
  PrintInBox("Finished Goods - Stock in hand")
  finalFinishedGoodsDict = CalculateFinishedGoodsSIH()
  finalFinishedGoodsDict = OrderedDict(sorted(finalFinishedGoodsDict.items()))
  for parts, qty in finalFinishedGoodsDict.iteritems():
    print("{:<15}{:15}".format(parts, qty))

def ShowRawMaterialSIHOnScreen():
  PrintInBox("Raw material - Stock in hand")
  finalPartsUsedDict = CalculateRawMaterialSIH()
  finalPartsUsedDict = OrderedDict(sorted(finalPartsUsedDict.items()))
  for part, qty in finalPartsUsedDict.iteritems():
    print("{:<15}{:15}".format(part, qty))
  return


def main():
  try:
    CheckConsistency()
    ShowRawMaterialSIHOnScreen()
    ShowFinishedGoodsSIHOnScreen()
  except MyException as ex:
    PrintInBox(str(ex))

if __name__ == "__main__":
  main()
