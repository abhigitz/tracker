###############################################################################
## Author: Ashish Anand
## Date: 2012-09-06 Thu 03:07 PM
## Intent: To check if the bills issued to have corresponding name in customer
## table
## Requirement: Python 3 Interpretor must be installed
##              Openpyxl for Python 3 must be installed
###############################################################################

from Util.Config import GetOption
from Util.Decorators import timeThisFunction
from Util.Exception import MyException
from Util.Misc import PrintInBox, ParseDateFromString, DD_MMM_YYYY
from Util.Persistent import Persistent

from whopaid.automatic_notifications import SendAutomaticSmsReportsIfRequired
from whopaid.customers_info import GetAllCustomersInfo
from whopaid.incoming_material import GetAllSuppliersDict
from whopaid.json_data_generator import AskUberObserverToUploadJsons
from whopaid.util_whopaid import GetAllCompaniesDict, SelectBillsAfterDate, ShrinkWorkingArea, GetWorkBookPath

from collections import defaultdict
import os

def SendAutomaticHeartBeat():
  #A heart beat will be sent every now and then whenever this function is called.
  #The receivers should not have any side effects and can expect back to back or no heartbeat at all. They should be resilient enough.
  CheckConsistency()
  AskUberObserverToUploadJsons()
  SendAutomaticSmsReportsIfRequired()
  ShrinkWorkingArea()
  return



class PersistentInfoForConsistencyCheck(Persistent):
  identifier = "LastModifiedTimeForBillsFile"
  def __init__(self):
    super(self.__class__, self).__init__(self.__class__.__name__)

  def isCheckRequired(self):
    if self.identifier not in self:
      return True #This is the first time it is called or persitent file was removed for some reason. Returning true so that check is made.
    return self[self.identifier] != os.path.getmtime(GetWorkBookPath())

  def saveNewFileTimeAtWhichConsistencyCheckWasDone(self):
    self[self.identifier] = os.path.getmtime(GetWorkBookPath())



def CheckConsistency():
  pcc = PersistentInfoForConsistencyCheck()

  if not pcc.isCheckRequired(): return #We successfully ran no need to check again.

  functionListForBills = [
      CheckCustomerExistenceInDB,
      ReportMissingOrDuplicateBillsSince,
      CheckBillingCategory,
      CheckBillsCalculation,
      CheckCancelledAmount,
      ReportUndeclaredProducts,
      ]

  allBillsDict = GetAllCompaniesDict().GetAllBillsOfAllCompaniesAsDict()
  for eachFunc in functionListForBills:
    eachFunc(allBillsDict)

  allSupplierDict = GetAllSuppliersDict().GetAllBillsOfAllSuppliersAsDict()
  functionListForIncomingMaterial = [
      CheckPartExistenceInBOM,
      ]
  for eachFunc in functionListForIncomingMaterial:
    eachFunc(allSupplierDict)

  pcc.saveNewFileTimeAtWhichConsistencyCheckWasDone()
  return

def CheckPartExistenceInBOM(allSupplierDict):
  from whopaid.bom import GetPartsNamesAsList
  partNames = GetPartsNamesAsList()
  for comp, bills in allSupplierDict.iteritems():
    for b in bills:
      if b.materialDesc not in partNames:
        raise MyException("The purchased part {} in bill#{} dt {} is not defined in BOM".format(b.materialDesc, int(b.billNumber), DD_MMM_YYYY(b.invoiceDate)))

def CheckCancelledAmount(allBillsDict):
  for (eachCompName, eachComp) in allBillsDict.iteritems():
    if eachCompName.lower().find("cancel") != -1:
      for eachBill in eachComp:
        if eachBill.amount != 0:
          raise MyException("Bill#{} dated {} is cancelled but has amount {}. It should be 0".format(eachBill.billNumber, str(eachBill.invoiceDate), eachBill.amount))


def CheckBillingCategory(allBillsDict):
  for (eachCompName, eachComp) in allBillsDict.iteritems():
    eachComp.CheckEachBillsBillingCategory()

def CheckBillsCalculation(allBillsDict):
  for (eachCompName, eachComp) in allBillsDict.iteritems():
    eachComp.CheckEachBillsCalculation()

def ReportUndeclaredProducts(allBillsDict):
  from bom import GetProductsNamesAsList
  billedProducts = set([b.modelDesc for comp, billList in allBillsDict.iteritems() for b in billList])
  bomProducts = GetProductsNamesAsList()
  for p in billedProducts:
    if p not in bomProducts:
      raise MyException("{} is not defined in BOM".format(p))
  return

def ReportMissingOrDuplicateBillsSince(allBillsDict):
  d = defaultdict(list)

  #First sort all bills category wise
  for eachCompName, eachComp in allBillsDict.iteritems():
    for eachBill in eachComp:
      d[eachBill.billingCategory].append(eachBill)

  dateAsString = GetOption("CONSISTENCY_CHECK_SECTION", "CheckMissingBillsSinceDate")
  startDateObject = ParseDateFromString(dateAsString)

  def _GetFinancialYear(bill):
    return bill.invoiceDate.year if (bill.invoiceDate.month > 3) else (bill.invoiceDate.year - 1)

  #In each category try to find missing bills in the permissible date range
  for eachCategory in d:
    if eachCategory.lower() in ["tracking"]:
      continue
    billList = d[eachCategory]
    billList = SelectBillsAfterDate(billList, startDateObject)
    billList.sort(key=lambda b:b.invoiceDate) #TODO: Remove

    if len(billList) < 1:
      continue  # i.e. if there is only one bill

    #Categorize bills year wise
    yearwiseDict = defaultdict(list)
    for eachBill in billList:
      yearwiseDict[_GetFinancialYear(eachBill)].append(int(eachBill.billNumber))

    #Try to find a missing bills in one year financial year span
    for eachYear in yearwiseDict:
      listOfBillsInOneYear = yearwiseDict[eachYear]
      minBill = min(listOfBillsInOneYear)
      maxBill = max(listOfBillsInOneYear)

      for billNumber in range(int(minBill) + 1, int(maxBill)):
        if billNumber not in listOfBillsInOneYear:
          raise MyException("Bill Number: %s missing in category %s in year starting from 1-Apr-%s" % (str(billNumber), eachCategory, eachYear))
        if listOfBillsInOneYear.count(billNumber) > 1:
          #raise MyException("Bill Number: %s is entered twice in category %s in year starting from 1-Apr-%s" % (str(billNumber), eachCategory, eachYear))
          # This condition is relaxed since more than one model can be shipped
          # to a single customer.
          pass

  return

def CheckCustomerExistenceInDB(allBillsDict):

  """ Execute various checks which cross verify that data entered matches.
      1. Every bill issued should have an existing customer in database
      2. Every payment received should have an existing customer in database.
      3. More to come...
  """
  uniqueCompNames = set([eachComp for eachComp in allBillsDict.keys()])

  allCustInfo = GetAllCustomersInfo()

  for eachComp in uniqueCompNames:
    if eachComp not in allCustInfo.keys():
      raise MyException("M\s {} not found in customer database".format(eachComp))
  return



@timeThisFunction
def main():
  try:
    CheckConsistency()
  except MyException as ex:
    PrintInBox(str(ex))

if __name__ == '__main__':
    main()
