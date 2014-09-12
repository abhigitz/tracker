"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"" Intent: To read the BOM file and have an in-memory
"" representation of it.
"" 2014-Sep-12 Fri 03:59 PM
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

from Util.Misc import GetPickledObject
from Util.Config import GetOption, GetAppDir

import os


class _AllBOMInfo(dict):
  """Base Class which is basically a dictionary.
  Key is compName and Value is a list of info"""
  def __init__(self, bomPath):
    super(_AllBOMInfo, self).__init__(dict())
    import yaml  # pip install PyYAML
    with open(bomPath) as bom:
      self.doc = yaml.load(bom)

  @property
  def allProductsNames(self):
    return list({products for products, values in self.doc.iteritems()})

  @property
  def allPartNames(self):
    return list({partNames for product, parts in self.doc.iteritems()
                 for partNames, partAttribs in parts.iteritems()})


def GetAllBOMInfo():
  """Pickled BOM is used if possible. Dont change any code here."""
  bomPath = os.path.join(
      GetAppDir(),
      GetOption("CONFIG_SECTION", "BOMRelativePath"))

  def _CreateAllBOMInfoObject(bomPath):
    return _AllBOMInfo(bomPath)

  return GetPickledObject(bomPath, createrFunction=_CreateAllBOMInfoObject)


def main():
  bom = GetAllBOMInfo()
  #For testing purposing printing names
  print("All Products encountered: {}".format(bom.allProductsNames))
  print("All Parts encountered: {}".format(bom.allPartNames))

if __name__ == "__main__":
  main()
