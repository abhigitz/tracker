#######################################################
## Date: 2014-Sep-13 Sat 11:07 AM
## Intent: To read bom file and store info
## Requirement: Python Interpretor must be installed
## Openpyxl must be installed
#######################################################
from Util.Misc import GetPickledObject
from Util.Config import GetOption, GetAppDir

import os

def GetProductsNamesAsList(bomPath):
  from Util.ExcelReader import LoadNonIterableWorkbook, GetColLetter
  wb = LoadNonIterableWorkbook(bomPath)
  productsNamesInRow = GetOption("CONFIG_SECTION", "BOMProductNameInRow")
  productsStartFromCol = GetOption("CONFIG_SECTION", "BOMProductsStartsAtCol")

  ws = wb.get_sheet_by_name(GetOption("CONFIG_SECTION", "NameOfBOMSheet"))
  MAX_COL = ws.get_highest_column()
  maxColLetter = GetColLetter(MAX_COL)
  ran = "{prnc}{prnr}:{mcl}{prnr}".format(prnr=productsNamesInRow, prnc=productsStartFromCol, mcl=maxColLetter)
  r = ws.range(ran)
  return [t.value for t in r[0]]


def GetPartsNamesAsList(bomPath):
  from Util.ExcelReader import LoadNonIterableWorkbook
  wb = LoadNonIterableWorkbook(bomPath)
  productsNamesInRow = GetOption("CONFIG_SECTION", "BOMProductNameInRow")
  partsNameInCol = GetOption("CONFIG_SECTION", "BOMPartsNameInCol")
  partsStartFromCol = int(productsNamesInRow) + 1

  ws = wb.get_sheet_by_name(GetOption("CONFIG_SECTION", "NameOfBOMSheet"))
  MAX_ROW = ws.get_highest_row()
  r= ws.range("{pnc}{psc}:{pnc}{mr}".format(pnc=partsNameInCol, psc=partsStartFromCol, mr=MAX_ROW))
  return [t[0].value for t in r]

class _AllBOMInfo(dict):
  """Base Class which is basically a dictionary. Key is compName and Value is a list of info"""
  def __init__(self, bomPath):
    super(_AllBOMInfo, self).__init__(dict())

    from Util.ExcelReader import LoadNonIterableWorkbook, GetColLetter
    wb = LoadNonIterableWorkbook(bomPath)
    ws = wb.get_sheet_by_name(GetOption("CONFIG_SECTION", "NameOfBOMSheet"))
    MAX_COL = ws.get_highest_column()
    MAX_ROW = ws.get_highest_row()
    maxColLetter = GetColLetter(MAX_COL)
    productsNamesInRow = GetOption("CONFIG_SECTION", "BOMProductNameInRow")
    dataStartsAtRow = int(productsNamesInRow) + 1
    productsStartFromCol = GetOption("CONFIG_SECTION", "BOMProductsStartsAtCol")
    ran = "{productsStartFromCol}{dataStartsAtRow}:{maxColLetter}{max_row}".format(productsStartFromCol=productsStartFromCol, dataStartsAtRow=dataStartsAtRow, maxColLetter=maxColLetter, max_row=MAX_ROW)
    data = ws.range(ran)
    productNamesList = GetProductsNamesAsList(bomPath)
    partNamesList = GetPartsNamesAsList(bomPath)
    for product in productNamesList:
      self[product] = dict()

    for i, partRow in enumerate(data):
      for j, partUsed in enumerate(partRow):
        self[productNamesList[j]][partNamesList[i]] = partUsed.value
    return


def GetBOM():
  bomPath = os.path.join(GetAppDir(), GetOption("CONFIG_SECTION", "BOMRelativePath"))
  def _(bomPath):
    return _AllBOMInfo(bomPath)
  return GetPickledObject(bomPath, createrFunction=_)


def main():
  bom = GetBOM()
  from Util.Misc import PrintInBox
  for product, parts in bom.items():
    PrintInBox("{} uses these parts".format(product))
    for i, (part, qty) in enumerate(parts.items(), start=1):
      print("{:<15}{:<15}:{}".format(i, part, qty))

  return

if __name__ == "__main__":
  main()
