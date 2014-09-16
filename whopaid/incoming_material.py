###############################################################################
## Author: Ashish Anand
## Date: 2014-Sep-13 Sat 03:02 PM
## Intent: To read incoming material from xlsx table and make sense out of it.
## Requirement: Python Interpretor must be installed
###############################################################################
from Util.Exception import MyException
from Util.Config import GetOption, GetAppDir
from Util.ExcelReader import LoadIterableWorkbook, GetCellValue, GetRows
from Util.Misc import GetPickledObject, ParseDateFromString


import os
import datetime

WRKBK_PATH_CONFIG_OPTION = "IncomingMaterialPath"
WRKBK_SHEET_NAME_CONFIG_OPTION = "NameOfIncomingMaterialSheet"
WRKBK_SHEET_DATA_STARTS_AT_ROW_CONFIG_OPTION = "IncomingMaterialDataStartsAtRow"

def _GetSupplierWorkBookPath():
    return os.path.join(GetAppDir(), GetOption("CONFIG_SECTION", WRKBK_PATH_CONFIG_OPTION))

def intx(i):
    return(0 if i is None else int(i))

def floatx(i):
    return(0.0 if i is None else float(i))

def datex(d):
    return(datetime.date.today() if d is None else d)


class SuppliersDict(dict):#TODO: Name it as DB
    """Base Class which is basically a dictionary. Key is compName and Value is a list of single bills of that company"""
    def __init__(self):
        super(SuppliersDict, self).__init__(dict())
        self[KIND.BILL] = dict()
        self[KIND.PAYMENT] = dict()
        self[KIND.ADJUSTMENT] = dict()
        self[KIND.ORDER] = dict()
        self[KIND.PUNTED_ORDER] = dict()


    def _AddEntry(self, typ, r):
        """
        The only method through which this master database is prepared.
        Find out if the company exists already. If it does, add the bill to that company.
        If it doesnt, create the company and add the bill to that company.
        typ = KIND.ORDER/BILL/PAYMENT/ADJUSTMENT
        """
        if r.compName in self[typ].keys():
            self[typ][r.compName].append(r)
        else:
            #If for this type there is no entry for this company, create it.
            self[typ][r.compName] = Supplier(r.compName) #TODO: Remove after testing
            self[typ][r.compName].append(r)

    def AddBill(self, b):
        self._AddEntry(KIND.BILL, b)

    def AddPayment(self, p):
        self._AddEntry(KIND.PAYMENT, p)

    def AddAdjustment(self, a):
        self._AddEntry(KIND.ADJUSTMENT, a)

    def AddOrder(self, o):
        self._AddEntry(KIND.ORDER, o)


    def GetAllBillsOfAllSuppliersAsDict(self):
        return self[KIND.BILL]

    def GetAllPaymentsByAllCompaniesAsDict(self):
        return self[KIND.PAYMENT]

    def GetAllAdjustmentsOfAllCompaniesAsDict(self):
        return self[KIND.ADJUSTMENT]

    def GetAllOrdersOfAllCompaniesAsDict(self):
        return self[KIND.ORDER]


    def GetBillsListForThisCompany(self, compName):
        return self.GetAllBillsOfAllSuppliersAsDict().get(compName, None)

    def GetPaymentsListForThisCompany(self, compName):
        return self.GetAllPaymentsByAllCompaniesAsDict().get(compName, None)

    def GetUnAccountedAdjustmentsListForCompany(self, compName):
      adjustmentList = self.GetAllAdjustmentsOfAllCompaniesAsDict().get(compName, [])
      return [a for a in adjustmentList if not a.adjustmentAccountedFor]

    def GetOrdersListForCompany(self, compName):
        return self.GetAllOrdersOfAllCompaniesAsDict().get(compName, None)


def GetAllSuppliersDict():
    workbookPath = _GetSupplierWorkBookPath()
    def _CreateAllSuppliersDict(workbookPath):
        return _AllSuppliersDict(workbookPath)
    return GetPickledObject(workbookPath, _CreateAllSuppliersDict)

class KIND(object):
    BILL = 1
    PAYMENT = 2
    ADJUSTMENT = 3
    ORDER = 4
    PUNTED_ORDER = 5

def GuessKindFromValue(val):
  if val:
    val = val.lower()
    if val.lower() == "bill": return KIND.BILL
    elif val.lower() == "payment": return KIND.PAYMENT
    elif val.lower() == "adjustment": return KIND.ADJUSTMENT
    elif val.lower() == "order": return KIND.ORDER
    elif val.lower() == "punted": return KIND.PUNTED_ORDER
  print("Returning {}".format(val))
  return None

def GuessKindFromRow(row):
  for cell in row:
    col = cell.column
    val = GetCellValue(cell)

    if col == SheetCols.KindOfEntery:
      return GuessKindFromValue(val)
  return None

class _AllSuppliersDict(SuppliersDict):
  """
  This class represents the heart of logic.
  It is an aggregation of all companies.
  It is a dictonary of dict. Ist level ["BILL"/"PAYMENT"]. Second level company names. Values are list of all bills or payments.
  Each member in the dict is a single company.
  Each Single company holds the list of all bills ever issued to them.
  """
  def __init__(self, workbookPath):
    super(_AllSuppliersDict, self).__init__()

    for row in GetRows(
      workbookPath=workbookPath,
      sheetName=GetOption("CONFIG_SECTION", WRKBK_SHEET_NAME_CONFIG_OPTION),
      firstRow=GetOption("CONFIG_SECTION", WRKBK_SHEET_DATA_STARTS_AT_ROW_CONFIG_OPTION),
      includeLastRow=False
      ):


        kind = GuessKindFromRow(row)
        if kind == KIND.BILL:
          self.AddBill(CreateSingleBillRow(row))
        elif kind == KIND.PAYMENT:
          self.AddPayment(CreateSinglePaymentRow(row))
        elif kind == KIND.ADJUSTMENT:
          self.AddAdjustment(CreateSingleAdjustmentRow(row))
        elif kind == KIND.ORDER:
          self.AddOrder(CreateSingleOrderRow(row))
        elif kind == KIND.PUNTED_ORDER:
          pass #DO NOT DO ANYTHING FOR PUNTED ORDERS
        else:
          raise Exception("Error in row number: {} Kind of entry is invalid".format(rowNumber))

class Supplier(list):
  """
  For us, the company is same as the list of all bills. If any further info is required, it needs some overhauling.
  """
  def __init__(self, name):
    super(Supplier, self).__init__(list())
    self.compName = name  # Use this name. Do not pick name from first bill.

  def __eq__(self, other):
    """
    Crude Check. If sum of bill numbers is same, then the two lists are same.
    """
    return sum([int(b.billNumber) for b in self]) == sum ([int(b.billNumber) for b in other])

  def __str__(self):
      res = "Supplier: M/s " + self.compName
      if len(self) > 0:
        for b in self:
          res += "\n" + str(b)
      else:
        res +=  " has no bills"

      return res

  def CheckEachBillsCalculation(self):
    for b in self:
      b.CheckCalculation()


class SingleRow(object):
  pass
class SinglePaymentRow(SingleRow):
  pass
class SingleAdjustmentRow(SingleRow):
  pass

class SingleOrderRow(SingleRow):
  pass

class SingleBillRow(SingleRow):
    """
    This class represents a single row in the excel sheet which in effect represents a single bill
    """
    def __init__(self):
        pass

    def __lt__(self, other): # Helps in just using sorted over a list of bills
        if self.invoiceDate < other.invoiceDate:
            return True
        elif self.invoiceDate == other.invoiceDate:
            return self.billNumber < other.billNumber
        else:
            return False

    def CheckCalculation(self):
        if intx(self.goodsValue) != 0:
            if(intx(self.amount) != (intx(self.goodsValue) + intx(self.tax) + intx(self.courier))):
              raise MyException("Calculation error in bill#{} billDate:".format(str(self.billNumber), self.invoiceDate))


def SelectBillsBeforeDate(billList, dateObject):
    if not dateObject:
        import pdb; pdb.set_trace()
    return [b for b in billList if dateObject >= ParseDateFromString(b.invoiceDate)]

def SelectBillsAfterDate(billList, dateObject):
    return [b for b in billList if dateObject <= ParseDateFromString(b.invoiceDate)]

class SheetCols:
    """
    This class is used as Enum.
    If and when the format of excel file changes just change the column bindings in this class
    """
    SupplierFriendlyNameCol = "A"
    KindOfEntery            = "B"
    InvoiceNumberCol        = "C"
    InvoiceDateCol          = "D"
    MaterialDesc            = "E"
    MaterialQty             = "F"
    GoodsValue              = "G"
    Tax                     = "H"
    Courier                 = "I"
    InvoiceAmount           = "J"

def CreateSingleOrderRow(row):
    r = SingleOrderRow()
    for cell in row:
        col = cell.column
        val = GetCellValue(cell)

        if col == SheetCols.SupplierFriendlyNameCol:
            if not val: raise Exception("Row: {} seems empty. Please fix the database".format(cell.row))
            r.compName = val
        elif col == SheetCols.KindOfEntery:
            r.kindOfEntery = val
        elif col == SheetCols.MaterialDesc:
            if not val: raise Exception("Order in row: {} seems empty. Please fix the database".format(cell.row))
            r.materialDesc = val
    return r

def CreateSingleAdjustmentRow(row):
    r = SingleAdjustmentRow()
    for cell in row:
        col = cell.column
        val = GetCellValue(cell)

        if col == SheetCols.SupplierFriendlyNameCol:
            if not val: raise Exception("No supplier name in row: {} and col: {}".format(cell.row, col))
            r.compName = val
        elif col == SheetCols.KindOfEntery:
            if not val: raise Exception("No type of entery in row: {} and col: {}".format(cell.row, col))
            r.kindOfEntery = val
        elif col == SheetCols.InvoiceAmount:
            if not val: raise Exception("No adjustment amount in row: {} and col: {}".format(cell.row, col))
            r.amount = val
        elif col == SheetCols.InvoiceDateCol:
            if val is not None:
                r.invoiceDate = ParseDateFromString(val)
            else:
                r.invoiceDate = val
        elif col == SheetCols.InvoiceNumberCol:
            r.adjustmentNo = val

    return r

def CreateSinglePaymentRow(row):
    r = SinglePaymentRow()
    for cell in row:
        col = cell.column
        val = GetCellValue(cell)

        if col == SheetCols.InvoiceAmount:
            if not val: raise Exception("No cheque amount in row: {} and col: {}".format(cell.row, col))
            r.amount = val
        elif col == SheetCols.KindOfEntery:
            if not val: raise Exception("No type of entery in row: {} and col: {}".format(cell.row, col))
            r.kindOfEntery = GuessKindFromValue(val)
        elif col == SheetCols.SupplierFriendlyNameCol:
            if not val: raise Exception("No supplier name in row: {}".format(cell.row))
            r.compName = val
    return r


def CreateSingleBillRow(row):
  b = SingleBillRow()
  for cell in row:
    col = cell.column
    val = GetCellValue(cell)

    b.rowNumber = cell.row
    if col == SheetCols.InvoiceAmount:
      b.amount = val
    elif col == SheetCols.KindOfEntery:
      if not val: raise Exception("No type of entery in row: {} and col: {}".format(cell.row, col))
      b.kindOfEntery = val
    elif col == SheetCols.InvoiceNumberCol:
      if not val: raise Exception("Row: {} seems not to have any bill number.".format(cell.row))
      b.billNumber = val
    elif col == SheetCols.SupplierFriendlyNameCol:
      if not val: raise Exception("Row: {} seems empty. Please fix the database".format(cell.row))
      b.compName = val
    elif col == SheetCols.Courier:
      b.courier = val
    elif col == SheetCols.InvoiceDateCol:
      if not val: raise Exception("No invoice date in row: {} and col: {}".format(cell.row, col))
      b.invoiceDate = ParseDateFromString(val)
    elif col == SheetCols.GoodsValue:
      #if not val: raise Exception("No goods value in row: {} and col: {}".format(cell.row, col))
      b.goodsValue = val
    elif col == SheetCols.Tax:
      #if not val: raise Exception("No tax in row: {} and col: {}".format(cell.row, col))
      b.tax = val
    elif col == SheetCols.MaterialDesc:
      if isinstance(val, basestring):
        b.materialDesc = val
      elif val is None:
        b.materialDesc = "--"
      else:
        raise Exception("The material description should be string and not {} in row: {} and col: {}".format(type(val), cell.row, col))
    elif col == SheetCols.MaterialQty:
      if val is not None:
        b.materialQty = int(val)
      else:
        b.materialQty = val
  return b

