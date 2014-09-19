###############################################################################
## Author: Ashish Anand
## Date: 2014-Sep-16 Tue 02:31 PM
## Intent: To read daliy production from xlsx table and make sense out of it.
## Requirement: Python Interpretor must be installed
###############################################################################
from Util.Config import GetOption, GetAppDir
from Util.ExcelReader import GetRows
from Util.Misc import GetPickledObject, ParseDateFromString, DD_MMM_YYYY

import os

WRKBK_PATH_CONFIG_OPTION = "DailyProductionPath"
WRKBK_SHEET_NAME_CONFIG_OPTION = "NameOfDailyProductionSheet"
WRKBK_SHEET_DATA_STARTS_AT_ROW_CONFIG_OPTION = "DailyProductionDataStartsAtRow"

def _GetDailyProductionPath():
    return os.path.join(GetAppDir(), GetOption("CONFIG_SECTION", WRKBK_PATH_CONFIG_OPTION))


class DailyProductionDict(dict):
  """Base Class which is basically a dictionary. Key is modelDesc and Value is a list of single daily productions for that material"""
  def __init__(self):
    super(DailyProductionDict, self).__init__(dict())
    self[KIND.DAILY_PRODUCTION] = dict()
    self[KIND.ADJUSTMENT] = dict()


  def _AddEntry(self, typ, r):
    """
    The only method through which this master database is prepared.
    Find out if the modelDesc exists already. If it does, add the row to that modelDesc.
    If it doesnt, create the modelDesc and add the row to that modelDesc.
    typ = KIND/DAILY_PRODUCTION/ADJUSTMENT
    """
    if r.modelDesc in self[typ].keys():
      self[typ][r.modelDesc].append(r)
    else:
      #If for this type there is no entry for this modelDesc, create it.
      self[typ][r.modelDesc] = list()
      self[typ][r.modelDesc].append(r)

  def AddDailyProductionRow(self, b):
    self._AddEntry(KIND.DAILY_PRODUCTION, b)

  def AddAdjustment(self, a):
    self._AddEntry(KIND.ADJUSTMENT, a)

  def GetDailyProdOfAllMaterialsAsDict(self):
    return self[KIND.DAILY_PRODUCTION]

  def GetAdjustmentsOfAllCompaniesAsDict(self):
    return self[KIND.ADJUSTMENT]

  def GetDailyProdListForThismodelDesc(self, modelDesc):
    return self.GetDailyProdOfAllMaterialsAsDict().get(modelDesc, None)


def GetDailyProductionDict():
    workbookPath = _GetDailyProductionPath()
    def _CreateDailyProductionDict(workbookPath):
      return _AllDailyProductionDict(workbookPath)
    return GetPickledObject(workbookPath, _CreateDailyProductionDict)

class KIND(object):
    DAILY_PRODUCTION = 1
    ADJUSTMENT = 2 # TODO: Implement it later if required

def _GuessKindFromRow(row):
  return KIND.DAILY_PRODUCTION

class _AllDailyProductionDict(DailyProductionDict):
  """
  This class represents the heart of logic.
  It is an aggregation of all companies.
  It is a dictonary of dict. Ist level ["DAILY_PRODUCTION"/"PAYMENT"]. Second level modelDesc names. Values are list of all bills or payments.
  Each member in the dict is a single modelDesc.
  Each Single modelDesc holds the list of all bills ever issued to them.
  """
  def __init__(self, workbookPath):
    super(_AllDailyProductionDict, self).__init__()
    for row in GetRows(
        workbookPath = workbookPath,
        sheetName = GetOption("CONFIG_SECTION", WRKBK_SHEET_NAME_CONFIG_OPTION),
        firstRow = GetOption("CONFIG_SECTION", WRKBK_SHEET_DATA_STARTS_AT_ROW_CONFIG_OPTION),
        includeLastRow=False):

      kind = _GuessKindFromRow(row)
      if kind == KIND.DAILY_PRODUCTION:
        self.AddDailyProductionRow(_CreateSingleDailyProductionRow(row))
      else:
        firstCell = row[0]
        raise Exception("Error in row number: {} Kind of entry is invalid".format(firstCell.row))
    return


class SingleRow(object):
  def __str__(self):
    return "{:<15}{:<15}{:<15}{:<15}".format(DD_MMM_YYYY(self.productionDate), self.indentNo, self.modelDesc, self.modelQty)


class _SheetCols:
  """
  This class is used as Enum.
  If and when the format of excel file changes just change the column bindings in this class
  """
  DateCol       = "A"
  IndentNoCol   = "B"
  ModelDescCol  = "C"
  ModelQtyCol   = "D"



def _CreateSingleDailyProductionRow(row):
  r = SingleRow()
  for cell in row:
    col = cell.column
    val = cell.value

    r.rowNumber = cell.row
    if col == _SheetCols.ModelDescCol:
      if isinstance(val, basestring):
        r.modelDesc = val
      else:
        raise Exception("The material description should be string and not {} in row: {} and col: {}".format(type(val), cell.row, col))
    elif col == _SheetCols.DateCol:
      if not val: raise Exception("No date in row: {} and col: {}".format(cell.row, col))
      r.productionDate = ParseDateFromString(val)
    elif col == _SheetCols.ModelQtyCol:
      if val is not None:
        r.modelQty = int(val)
      else:
        r.modelQty = val
    elif col == _SheetCols.IndentNoCol:
      r.indentNo = val

  return r


if __name__=="__main__":

  dp = GetDailyProductionDict()
  allProd = dp.GetDailyProdOfAllMaterialsAsDict()
  for products, dpRows in allProd.iteritems():
    for row in dpRows:
      print(row)
