#######################################################
## Date: 2014-Sep-13 Sat 11:07 AM
## Intent: To read bom file and store info
## Requirement: Python Interpretor must be installed
## Openpyxl must be installed
#######################################################
from Util.Config import GetOption, GetAppDir
from Util.Decorators import memoize
from Util.ExcelReader import LoadNonIterableWorkbook, GetColLetter
from Util.Exception import MyException
from Util.Misc import GetPickledObject

import os

def GetBOMPath():
  return  os.path.join(GetAppDir(), GetOption("CONFIG_SECTION", "BOMRelativePath"))

def GetProductsNamesAsList():
  bomPath = GetBOMPath()
  wb = LoadNonIterableWorkbook(bomPath)
  productsNamesInRow = GetOption("CONFIG_SECTION", "BOMProductNameInRow")
  productsStartFromCol = GetOption("CONFIG_SECTION", "BOMProductsStartsAtCol")

  ws = wb.get_sheet_by_name(GetOption("CONFIG_SECTION", "NameOfBOMSheet"))
  MAX_COL = ws.get_highest_column()
  maxColLetter = GetColLetter(MAX_COL)
  ran = "{prnc}{prnr}:{mcl}{prnr}".format(prnr=productsNamesInRow, prnc=productsStartFromCol, mcl=maxColLetter)
  r = ws.range(ran)
  return [t.value for t in r[0]]


def GetReferenceLevelAsList():
  bomPath = GetBOMPath()
  wb = LoadNonIterableWorkbook(bomPath)
  productsNamesInRow = GetOption("CONFIG_SECTION", "BOMProductNameInRow")
  refLevelCol = GetOption("CONFIG_SECTION", "BOMReferenceLevelInCol")
  partsStartFromCol = int(productsNamesInRow) + 1

  ws = wb.get_sheet_by_name(GetOption("CONFIG_SECTION", "NameOfBOMSheet"))
  maxRowNumber = ws.get_highest_row()
  r= ws.range("{rlc}{psc}:{rlc}{mr}".format(rlc=refLevelCol, psc=partsStartFromCol, mr=maxRowNumber))
  return [t[0].value for t in r]


@memoize
def GetPartsNamesAsList():
  bomPath = GetBOMPath()
  wb = LoadNonIterableWorkbook(bomPath)
  productsNamesInRow = GetOption("CONFIG_SECTION", "BOMProductNameInRow")
  partsNameInCol = GetOption("CONFIG_SECTION", "BOMPartsNameInCol")
  partsStartFromCol = int(productsNamesInRow) + 1

  ws = wb.get_sheet_by_name(GetOption("CONFIG_SECTION", "NameOfBOMSheet"))
  maxRowNumber = ws.get_highest_row()
  r= ws.range("{pnc}{psc}:{pnc}{mr}".format(pnc=partsNameInCol, psc=partsStartFromCol, mr=maxRowNumber))
  return [t[0].value for t in r]

@memoize
def GetReferenceLevelQtyForPart(part):
  partNamesList = GetPartsNamesAsList()
  if part not in partNamesList:
    raise MyException("Part {} is not defined in BOM".format(part))
  return GetReferenceLevelAsList()[partNamesList.index(part)]

class _AllBOMInfo(dict):
  """Base Class which is basically a dictionary. Key is compName and Value is a list of info"""
  def __init__(self, bomPath):
    super(_AllBOMInfo, self).__init__(dict())

    wb = LoadNonIterableWorkbook(bomPath)
    ws = wb.get_sheet_by_name(GetOption("CONFIG_SECTION", "NameOfBOMSheet"))

    maxRowNumber = ws.get_highest_row()
    maxColLetter = GetColLetter(ws.get_highest_column())

    dataStartsAtRow = int(GetOption("CONFIG_SECTION", "BOMProductNameInRow")) + 1
    productsStartFromCol = GetOption("CONFIG_SECTION", "BOMProductsStartsAtCol")

    working_range = "{productsStartFromCol}{dataStartsAtRow}:{maxColLetter}{maxRowNumber}".format(productsStartFromCol=productsStartFromCol, dataStartsAtRow=dataStartsAtRow, maxColLetter=maxColLetter, maxRowNumber=maxRowNumber)

    working_data = ws.range(working_range)
    productNamesList = GetProductsNamesAsList()
    partNamesList = GetPartsNamesAsList()
    for productName in productNamesList:
      #Initialising all the products as empty dictionary
      self[productName] = dict()

    for i, partRow in enumerate(working_data):
      for j, partUsed in enumerate(partRow):
        self[productNamesList[j]][partNamesList[i]] = partUsed.value
    return

  def partsAndQtyForThisProductAsDict(self, product):
    return self[product]



def GetBOM():
  bomPath = GetBOMPath()
  def _PickledBOMInfo(bomPath):
    return _AllBOMInfo(bomPath)
  return GetPickledObject(bomPath, createrFunction=_PickledBOMInfo)


def main():
  bom = GetBOM()
  from Util.Misc import PrintInBox
  for product, parts in bom.items():
    PrintInBox("{} uses these parts".format(product))
    for i, (part, qty) in enumerate(parts.items(), start=1):
      print("{:<15}{:<15}:{}".format(i, part, qty))
  print(GetReferenceLevelAsList())

  return

if __name__ == "__main__":
  main()
