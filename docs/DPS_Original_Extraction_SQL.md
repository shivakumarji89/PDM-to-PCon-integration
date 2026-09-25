# DPS — Legacy Original Data Extraction SQL

Auto-extracted from the legacy DPS C# source (`c:/Users/siaoca/Desktop/PDM/DPS`). Each entry shows the source file,
line number, and the SQL flattened from C# string concatenation (`{expr}` marks an interpolated C# variable/expression).

> Extraction is heuristic: bare stored-proc-name strings and dynamically-built fragments may be partial. Review against source.

**Files with SQL:** 46  |  **Total statements:** 908

## AddNewControl.cs  (10)

### AddNewControl.cs#1 — line 486
```sql
SELECT AttributeType FROM Attribute WHERE AttributeId = {Conversions.ToString(currentId)}
```

### AddNewControl.cs#2 — line 551
```sql
SELECT Name, DescriptionId FROM Attribute WHERE AttributeId = {Conversions.ToString(currentId)}
```

### AddNewControl.cs#3 — line 559
```sql
UPDATE Attribute SET Name = '{Strings.Trim(NameBox.Text)}' WHERE AttributeId = {Conversions.ToString(currentId)}
```

### AddNewControl.cs#4 — line 567
```sql
SELECT Name, DescriptionId FROM [Option] WHERE OptionId = {Conversions.ToString(currentId)}
```

### AddNewControl.cs#5 — line 575
```sql
UPDATE [Option] SET Name = '{Strings.Trim(NameBox.Text)}' WHERE OptionId = {Conversions.ToString(currentId)}
```

### AddNewControl.cs#6 — line 604
```sql
UPDATE [{text2}] SET DisplayOrder = {Conversions.ToString(i)} WHERE {text2}Id = {Conversions.ToString(num4)}
```

### AddNewControl.cs#7 — line 671
```sql
SELECT Name, DisplayOrder FROM [{text2}] WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND DisplayOrder < 900 ORDER BY DisplayOrder
```

### AddNewControl.cs#8 — line 692
```sql
SELECT DisplayOrder FROM [{text2}] WHERE {text2}Id = {Conversions.ToString(currentId)}
```

### AddNewControl.cs#9 — line 750
```sql
SELECT DisplayOrder FROM [{text2}] WHERE {text2}Id = {Conversions.ToString(currentId)}
```

### AddNewControl.cs#10 — line 758
```sql
SELECT {text2}Id, Name, DisplayOrder FROM [{text2}] WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND DisplayOrder < 900
```

## AddNewData.cs  (13)

### AddNewData.cs#1 — line 324
```sql
SELECT DISTINCT optval.Name AS Fabric, optval.OrderCodeValue AS OrderCode FROM [Option] INNER JOIN OptionValue optval ON [Option].OptionId = optval.OptionId WHERE optval.OptionValueId = -1
```

### AddNewData.cs#2 — line 348
```sql
SELECT DISTINCT optval.Name AS FabricColour, optval.OrderCodeValue AS OrderCode, '' AS FabricParent FROM [Option] INNER JOIN OptionValue optval ON [Option].OptionId = optval.OptionId WHERE optval.OptionValueId = -1
```

### AddNewData.cs#3 — line 387
```sql
SELECT optval.OptionValueId, [Option].Name AS opt_name, optval.Status, optval.Name, optval.OrderCodeValue FROM OptionValue optval INNER JOIN [Option] ON optval.OptionId = [Option].OptionId WHERE optval.Status = 1 AND optval.OptionValueId NOT IN (SELECT OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = {Conversions.ToString(_catalogueId)}) AND [Option].IsFabric = 1 ORDER BY [Option].DisplayOrder, [Option].OptionId, optval.OrderCodeValue
```

### AddNewData.cs#4 — line 402
```sql
SELECT DISTINCT opt.OptionId FROM [Option] opt INNER JOIN OptionValue optval ON opt.OptionId = optval.OptionId INNER JOIN CatalogueOptionValues cov ON optval.OptionValueId = cov.OptionValueId WHERE opt.IsFabric = 1 AND cov.CatalogueId = {Conversions.ToString(_catalogueId)}
```

### AddNewData.cs#5 — line 411
```sql
SELECT optval.OptionValueId, optval.Status, [Option].Name AS opt_name, optval.Name, optval2.Name AS parent_name, optval.OrderCodeValue FROM OptionValue optval INNER JOIN [Option] ON optval.OptionId = [Option].OptionId INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId INNER JOIN OptionValue optval2 ON dov.OptionValueId = optval2.OptionValueId WHERE /*optval.Status = 1 AND*/ optval.OptionValueId NOT IN (SELECT OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = {Conversions.ToString(_catalogueId)}) AND [Option].IsFabric = 2 AND optval2.OptionId IN (
```

### AddNewData.cs#6 — line 548
```sql
SELECT IsFabric FROM [Option] WHERE OptionId = {Conversions.ToString(parentOptionId)}
```

### AddNewData.cs#7 — line 556
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription ORDER BY DescriptionId DESC
```

### AddNewData.cs#8 — line 565
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num6)}, 1, '{text4}', 'OptionValue')
```

### AddNewData.cs#9 — line 583
```sql
INSERT INTO OptionValue (OptionId, Name, OrderCodeValue, DescriptionId, Status, SupplierId, ImageFile, CADMaterial) VALUES ({Conversions.ToString(parentOptionId)}, '{text4}', '{text2}', {Conversions.ToString(num6)}, 0, 1
```

### AddNewData.cs#10 — line 589
```sql
SELECT TOP 1 OptionValueId FROM OptionValue WHERE Name = '{text4}' AND OrderCodeValue = '{text2}' AND DescriptionId = {Conversions.ToString(num6)} ORDER BY OptionValueId DESC
```

### AddNewData.cs#11 — line 600
```sql
INSERT INTO DependentOptionValues (OptionValueId, AdditionalOptionValueId) VALUES ({, _parentIds[_parentValues.IndexOf(RuntimeHelpers.GetObjectValue(DataGrid1[num3, 2]))]),}, {), num7),}){))}
```

### AddNewData.cs#12 — line 604
```sql
INSERT INTO CatalogueOptionValues (CatalogueId, OptionValueId) VALUES ({Conversions.ToString(_catalogueId)}, {Conversions.ToString(num7)})
```

### AddNewData.cs#13 — line 622
```sql
INSERT INTO CatalogueOptionValues (CatalogueId, OptionValueId) VALUES ({Conversions.ToString(_catalogueId)}, {, NewLateBinding.LateGet(_selectionList[num3], null,}Tag{, new object[0], null, null, null)),}){))}
```

## AttributeValidator.cs  (29)

### AttributeValidator.cs#1 — line 714
```sql
SELECT DISTINCT Product.ProductId, Product.Product FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} ORDER BY Product.Product
```

### AttributeValidator.cs#2 — line 726
```sql
SELECT DISTINCT Product.ProductId, Product.Product, parent_item.ItemId FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId INNER JOIN Item parent_item ON itco.ItemId = parent_item.ItemId INNER JOIN Product parent_product ON parent_item.ProductId = parent_product.ProductId INNER JOIN ProductRange pr ON parent_product.ProductRangeId = pr.ProductRangeId WHERE pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} ORDER BY Product.Product
```

### AttributeValidator.cs#3 — line 768
```sql
SELECT ItemId, Item FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} ORDER BY Item
```

### AttributeValidator.cs#4 — line 779
```sql
SELECT Product FROM Product WHERE ProductId = {Conversions.ToString(productId)}
```

### AttributeValidator.cs#5 — line 795
```sql
SELECT attr.AttributeId, attr.Name AS attr_name, atval.AttributeValueId, atval.Name AS atval_name, atval.OrderCodeValue FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE atval.AttributeValueId IN (
```

### AttributeValidator.cs#6 — line 866
```sql
SELECT attr.AttributeId, attr.Name AS attr_name, atval.AttributeValueId, atval.Name AS atval_name, atval.OrderCodeValue, attr.AttributeType FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId INNER JOIN ProductAttributeValues pav ON atval.AttributeValueId = pav.AttributeValueId WHERE pav.ProductId = {, _productIdList[product_list.SelectedIndex]),} {),}ORDER BY attr.DisplayOrder, atval.DisplayOrdinal{))}
```

### AttributeValidator.cs#7 — line 920
```sql
SELECT attr.AttributeId, attr.Name AS attr_name, atval.AttributeValueId, atval.Name AS atval_name, atval.OrderCodeValue FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId INNER JOIN BaseAttributeValues bav ON atval.AttributeValueId = bav.AttributeValueId WHERE bav.ItemId = '{_itemIdList[item_list.SelectedIndex].ToString()}' ORDER BY attr.DisplayOrder, atval.DisplayOrdinal
```

### AttributeValidator.cs#8 — line 1042
```sql
SELECT attr.AttributeType FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE atval.AttributeValueId = {Conversions.ToString(atvalId)}
```

### AttributeValidator.cs#9 — line 1081
```sql
INSERT INTO BaseAttributeValues (ItemId, AttributeValueId) VALUES ({Conversions.ToString(num)}, {Conversions.ToString(num2)})
```

### AttributeValidator.cs#10 — line 1086
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### AttributeValidator.cs#11 — line 1090
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### AttributeValidator.cs#12 — line 1100
```sql
INSERT INTO PDMAudit.dbo.BAVUpdates (TransactionId, ItemId, AttributeValueId, ActionTaken) VALUES ({Conversions.ToString(num3)}, {Conversions.ToString(num)}, {Conversions.ToString(num2)}, 'ADDED')
```

### AttributeValidator.cs#13 — line 1151
```sql
SELECT DISTINCT Product.Product, pav.AttributeValueId AS pav_atvalId, mpv.AttributeValueId AS mpv_atvalId FROM Product INNER JOIN ProductAttributeValues pav On Product.ProductId = pav.ProductId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId And attr.AttributeType = 0 LEFT OUTER JOIN MaterialProductIdValues mpv ON pav.AttributeValueId = mpv.AttributeValueId WHERE Product.ProductId = {Conversions.ToString(productId)}
```

### AttributeValidator.cs#14 — line 1176
```sql
INSERT INTO ProductAttributeValues (ProductId, AttributeValueId) VALUES ({Conversions.ToString(productId)}, {Conversions.ToString(atvalId)})
```

### AttributeValidator.cs#15 — line 1181
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### AttributeValidator.cs#16 — line 1185
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### AttributeValidator.cs#17 — line 1195
```sql
INSERT INTO PDMAudit.dbo.PAVUpdates (TransactionId, ProductId, AttributeValueId, ActionTaken) VALUES ({Conversions.ToString(num3)}, {Conversions.ToString(productId)}, {Conversions.ToString(atvalId)}, 'ADDED')
```

### AttributeValidator.cs#18 — line 1238
```sql
SELECT DISTINCT Product.Product, pav.AttributeValueId AS pav_atvalId, mpv.AttributeValueId AS mpv_atvalId FROM Product INNER JOIN ProductAttributeValues pav On Product.ProductId = pav.ProductId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER Join Attribute attr ON atval.AttributeId = attr.AttributeId And attr.AttributeType = 0 LEFT OUTER JOIN MaterialProductIdValues mpv ON pav.AttributeValueId = mpv.AttributeValueId WHERE Product.ProductId = {Conversions.ToString(num)}
```

### AttributeValidator.cs#19 — line 1318
```sql
SELECT DISTINCT Product.Product, pav.AttributeValueId AS pav_atvalId, mpv.AttributeValueId AS mpv_atvalId FROM Product INNER JOIN ProductAttributeValues pav On Product.ProductId = pav.ProductId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER Join Attribute attr ON atval.AttributeId = attr.AttributeId And attr.AttributeType = 0 LEFT OUTER JOIN MaterialProductIdValues mpv ON pav.AttributeValueId = mpv.AttributeValueId WHERE Product.ProductId = {Conversions.ToString(num)}
```

### AttributeValidator.cs#20 — line 1390
```sql
SELECT DISTINCT Product.Product, pav.AttributeValueId AS pav_atvalId, mpv.AttributeValueId AS mpv_atvalId FROM Product INNER JOIN ProductAttributeValues pav On Product.ProductId = pav.ProductId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER Join Attribute attr ON atval.AttributeId = attr.AttributeId And attr.AttributeType = 0 LEFT OUTER JOIN MaterialProductIdValues mpv ON pav.AttributeValueId = mpv.AttributeValueId WHERE Product.ProductId = {Conversions.ToString(num)}
```

### AttributeValidator.cs#21 — line 1419
```sql
DELETE FROM ProductAttributeValues WHERE ProductId = {Conversions.ToString(num)} AND AttributeValueId = {Conversions.ToString(num2)}
```

### AttributeValidator.cs#22 — line 1424
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### AttributeValidator.cs#23 — line 1428
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### AttributeValidator.cs#24 — line 1438
```sql
INSERT INTO PDMAudit.dbo.PAVUpdates (TransactionId, ProductId, AttributeValueId, ActionTaken) VALUES ({Conversions.ToString(num5)}, {Conversions.ToString(num)}, {Conversions.ToString(num2)}, 'REMOVED')
```

### AttributeValidator.cs#25 — line 1491
```sql
DELETE FROM BaseAttributeValues WHERE ItemId = {Conversions.ToString(num)} AND AttributeValueId = {Conversions.ToString(num2)}
```

### AttributeValidator.cs#26 — line 1496
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### AttributeValidator.cs#27 — line 1499
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### AttributeValidator.cs#28 — line 1508
```sql
INSERT INTO PDMAudit.dbo.BAVUpdates (TransactionId, ItemId, AttributeValueId, ActionTaken) VALUES ({Conversions.ToString(num3)}, {Conversions.ToString(num)}, {Conversions.ToString(num2)}, 'REMOVED')
```

### AttributeValidator.cs#29 — line 1557
```sql
SELECT atval.AttributeValueId, attr.Name AS attr_name, atval.Name FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId
```

## AuthenticateUser.cs  (1)

### AuthenticateUser.cs#1 — line 64
```sql
SELECT UserId, DefaultDealerNum, DefaultSiteId, DefaultLanguageId, DefaultCurrencyId, DefaultCatalogueId, PDMAdministrator, DatabasePublication, HandbookPublication, SytelineExport, CoreMaintenance, ItemMaintenance, FormulaMaintenance, CurrencyMaintenance, ProductCodeMaintenance, SiteMaintenance, ProductMaintenance, SuperProductMaintenance, PriceMaintenance, CatalogueMaintenance, DescriptionMaintenance, PDMAuditer, PDMTester, ( SELECT BOMManager FROM PDMUserPrivileges p2 WHERE p2.UserId = p1.UserId ) AS BOMManager FROM PDMUserPrivileges p1 CROSS JOIN ( SELECT NULL AS BOMManager) x WHERE p1.UserName = '{username}'
```

## BOM_DeletedTreeMenu.cs  (11)

### BOM_DeletedTreeMenu.cs#1 — line 181
```sql
Delete Permanently
```

### BOM_DeletedTreeMenu.cs#2 — line 265
```sql
select 1 from materialdata where materialcriteriaid = '{text}'{, sqlConnection)}
```

### BOM_DeletedTreeMenu.cs#3 — line 270
```sql
delete from materialcriteria where materialcriteriaid = '{text}'
```

### BOM_DeletedTreeMenu.cs#4 — line 294
```sql
delete from materialsubjob where subjobmaterialid = '{array3[2]}' and materialid = '{array3[1]}' and ISNULL(opernum,10) = '{array3[0]}' and issubjob = 1 and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{, sqlConnection)}
```

### BOM_DeletedTreeMenu.cs#5 — line 306
```sql
delete from materialdata where materialproductid = '{Conversions.ToString(MaterialProductId)}' and siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and OperNum = '{array4[0]}'
```

### BOM_DeletedTreeMenu.cs#6 — line 321
```sql
delete from MaterialSubJob where SubjobMaterialId = '{array5[1]}' and MaterialId = '{array6[1]}' and ISNULL(opernum,10) = '{array6[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{, sqlConnection)}
```

### BOM_DeletedTreeMenu.cs#7 — line 349
```sql
delete from materialdata from materialdata inner join material on materialdata.materialid = material.materialid where materialcriteriaid = '{Conversions.ToString(CriteriaId)}' and material.materialid = '{Conversions.ToString(MaterialId)}' and materialdata.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and materialproductid = '{Conversions.ToString(MaterialProductId)}' and OperNum = '{Conversions.ToString(OperNum)}' and materialdata.issubjob = '{Conversions.ToString(isSubjob)}'
```

### BOM_DeletedTreeMenu.cs#8 — line 404
```sql
update materialdata set deletestatus = 0 from materialdata inner join material on materialdata.materialid = material.materialid where materialdata.issubjob = 0 and materialcriteriaid = '{text2}' and material.materialid = '{array[0]}' and materialdata.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and materialproductid = '{Conversions.ToString(MaterialProductId)}' and OperNum = '{text}'{, sqlConnection)}
```

### BOM_DeletedTreeMenu.cs#9 — line 419
```sql
Update materialdata set deletestatus = 0 from materialdata inner join material on materialdata.materialid = material.materialid where materialdata.issubjob = 1 and materialcriteriaid = '{text2}' and material.materialid = '{array3[1]}' and materialdata.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and materialproductid = '{Conversions.ToString(MaterialProductId)}' and OperNum = '{array3[0]}'{, sqlConnection)}
```

### BOM_DeletedTreeMenu.cs#10 — line 431
```sql
update materialsubjob set deletestatus = 0 from materialsubjob where subjobmaterialid = '{array4[2]}' and materialid = '{array4[1]}' and ISNULL(opernum,10) = '{array4[0]}' and issubjob = 1 and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{, sqlConnection)}
```

### BOM_DeletedTreeMenu.cs#11 — line 445
```sql
update materialsubjob set deletestatus = 0 from MaterialSubJob where SubjobMaterialId = '{array5[1]}' and MaterialId = '{array6[1]}' and ISNULL(opernum,10) = '{array6[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{, sqlConnection)}
```

## BOM_ExtractItemList.cs  (29)

### BOM_ExtractItemList.cs#1 — line 779
```sql
exec Material_ItemList_CatalogueAtt '{Conversions.ToString(Global.catalogueId)}', '{_ProductId}', '{_Attribute}', '{Conversions.ToString(sendType)}'{, sqlConnection)}
```

### BOM_ExtractItemList.cs#2 — line 791
```sql
SELECT Item.Item FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId
```

### BOM_ExtractItemList.cs#3 — line 815
```sql
SELECT atval.AttributeValueId, attr.Name, attr.Name + ' - ' + atval.Name AS NamePair, atval.productmaskvalue, attr.Attributeid, isnull(substring(atval.productmaskvalue, 0, charindex('|', atval.productmaskvalue)), '') as paravalue, attr.DisplayOrder, atval.DisplayOrdinal FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND attr.ProductCategoryId = '{Conversions.ToString(Global.categoryId)}' AND (atval.OrderCodeValue IS NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) AND attr.DisplayOrder > 1) ) and atval.attributevalueid in (select attributevalueid from ProductAttributeValues where productid = '{Conversions.ToString(Global.productId)}') and atval.attributevalueid in (select attributevalueid from CatalogueAttributeValues where catalogueid = '{Conversions.ToString(Global.catalogueId)}') ORDER BY attr.DisplayOrder, atval.DisplayOrdinal
```

### BOM_ExtractItemList.cs#4 — line 827
```sql
exec Material_ItemList_CatalogueAtt '{Conversions.ToString(Global.catalogueId)}', '{Conversions.ToString(Global.productId)}', '{_Attribute}', '1'{, sqlConnection)}
```

### BOM_ExtractItemList.cs#5 — line 1043
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'
```

### BOM_ExtractItemList.cs#6 — line 1093
```sql
SELECT compitem.Item AS component, itco.Quantity, itco.ComponentSequence FROM Item INNER JOIN ItemComponents itco ON itco.ItemId = Item.ItemId INNER JOIN Item compitem ON compitem.ItemId = itco.SubItemId WHERE Item.Item = '{itemChecked.ToString()}'
```

### BOM_ExtractItemList.cs#7 — line 1116
```sql
exec Material_BOM_Extract '{arrayList[i].ToString()}', {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}, '{RowPointer}'{) : (}exec MaterialItemBOM '{arrayList[i].ToString()}', '{featstr_textbox.Text.Replace(} {,}|{)}', '{RowPointer}', '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{))}
```

### BOM_ExtractItemList.cs#8 — line 1160
```sql
exec Material_Extract_CalculateCost '{RowPointer}', '{_SLServer}.{_SLDatabase}'
```

### BOM_ExtractItemList.cs#9 — line 1168
```sql
exec Material_Extract_MaterialStatus {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}, '{RowPointer}'
```

### BOM_ExtractItemList.cs#10 — line 1215
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'
```

### BOM_ExtractItemList.cs#11 — line 1259
```sql
SELECT DISTINCT AttVal, Opt, ParentItem, Material, OptionCode, Description, Qty, Scrapfactor, Oper_num, IsSubJob, Cost, level, test_status, live_status, FamilyCode, RGIDDesc, OperDesc FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}' AND Material <> '' ORDER BY AttVal, Opt, ParentItem, Material
```

### BOM_ExtractItemList.cs#12 — line 1327
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'
```

### BOM_ExtractItemList.cs#13 — line 1405
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'
```

### BOM_ExtractItemList.cs#14 — line 1416
```sql
exec Material_Extract_CalculateCost '{RowPointer}', '{_SLServer}.{_SLDatabase}'
```

### BOM_ExtractItemList.cs#15 — line 1425
```sql
exec Material_Extract_MaterialStatus {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}, '{RowPointer}'
```

### BOM_ExtractItemList.cs#16 — line 1437
```sql
SELECT parentitem,SUM(cost) AS totalCost FROM material_extract WITH(NOLOCK) WHERE material_extract.rowpointer = '{RowPointer}' and level = 1 GROUP BY parentitem
```

### BOM_ExtractItemList.cs#17 — line 1497
```sql
SELECT DISTINCT AttVal, Opt, ParentItem, Material, OptionCode, Material_Extract.Description, Qty, Scrapfactor, Oper_num, IsSubJob, Cost, level, test_status, live_status, FamilyCode, RGIDDesc, OperDesc FROM dbo.Material_Extract WHERE Material_Extract.rowpointer = '{RowPointer}' AND Material_Extract.material <> '' ORDER BY AttVal, Opt, parentitem, material
```

### BOM_ExtractItemList.cs#18 — line 1584
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'
```

### BOM_ExtractItemList.cs#19 — line 1601
```sql
SELECT TOP 1 Product FROM Product WITH(NOLOCK) WHERE ProductId = {_ProductId}
```

### BOM_ExtractItemList.cs#20 — line 1685
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'
```

### BOM_ExtractItemList.cs#21 — line 1754
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'
```

### BOM_ExtractItemList.cs#22 — line 1763
```sql
exec MaterialProductBOM '{objectValue.ToString()}', '{RowPointer}', {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}
```

### BOM_ExtractItemList.cs#23 — line 1785
```sql
SELECT DISTINCT ParentItem, Material, Description from Material_Extract WITH(NOLOCK) WHERE rowpointer ='{RowPointer}'
```

### BOM_ExtractItemList.cs#24 — line 1898
```sql
SELECT DISTINCT createdate,createdby, recorddate,updatedby,item, 'no' as 'Super Prod', item_mst.Description, stat as Status, '' as 'Reason Code',0 as 'Eurobase', 0 as Cost, '' as Eurr, '' as Vendor, product_code as 'P/L', '' as Cube, 0 as Weight, case when stocked = 1 then 'yes' else 'no' end Stocked, lead_time as 'Lead Time', 0 as 'Pre-EngineeringLeadtime', 0 as 'Pre-ProductionLeadtime', '' as Drawing,'' as Handbook, '' as CNCItem, isnull(plan_code,'') as planner, days_supply as 'Days Supply','' as 'Manf Offset', U_m as UM, comm_code as 'Commodity Code', p_m_t_code as 'P/M', '' as 'Manu Master', Case when phantom_flag = 0 then 'no' else 'yes' end Phantom, isnull(feat_templ,'') as Template, '' as 'ECO no.',''as 'ECO date', STUFF((SELECT '|' + convert(varchar, jobroute_mst.WC)+'|'+convert(varchar,jobroute_mst.oper_num) FROM {Global.SytelineLiveDatabase}.dbo.jobroute_mst WITH(NOLOCK) WHERE jobroute_mst.job = item_mst.job and jobroute_mst.suffix = item_mst.suffix and jobroute_mst.site_ref = item_mst.site_ref ORDER BY jobroute_mst.oper_num FOR XML PATH('') ), 1, 1, '') AS 'Work Centre', STUFF((SELECT '|' + convert(varchar, jrt_sch_mst.queue_hrs)+'|'+convert(varchar,jrt_sch_mst.oper_num) FROM {Global.SytelineLiveDatabase}.dbo.jrt_sch_mst WITH(NOLOCK) WHERE jrt_sch_mst.job = item_mst.job and jrt_sch_mst.suffix = item_mst.suffix and jrt_sch_mst.site_ref = item_mst.site_ref ORDER BY jrt_sch_mst.oper_num FOR XML PATH('') ), 1, 1, '') AS 'Queue', STUFF((SELECT '|' + convert(varchar, jrt_sch_mst.run_lbr_hrs)+'|'+convert(varchar,jrt_sch_mst.oper_num) FROM {Global.SytelineLiveDatabase}.dbo.jrt_sch_mst WITH(NOLOCK) WHERE jrt_sch_mst.job = item_mst.job and jrt_sch_mst.suffix = item_mst.suffix and jrt_sch_mst.site_ref = item_mst.site_ref ORDER BY jrt_sch_mst.oper_num FOR XML PATH('') ), 1, 1, '') as 'Run time', family_code as 'Family Code','' as Feat1,'' as Feat2,''as Feat3, '' as Feat4,''as Feat5,''as Feat6,''as Feat7,''as Feat8,''as Feat9,''as Feat10, ''as Feat11,''as Feat12,''as Feat13,''as Feat14,''as Feat15,''as Feat16,''as Feat17,''as Feat18,''as Feat19,''as feat20,''as SiteRef,'' Qty, case when matl_type = 'M' then 'Material' when matl_type = 'O' then 'Other' end MatlType, order_min as OrderMin, order_mult as OrderMult,accept_req as AcceptReq,plan_flag as PlanFlag, paper_time as PaperTime,dock_time as DockTime,isnull(alt_item,'') as AltItem,isnull(weight_units,'') as WeightUnits, BackFlush,isnull(bflush_loc,'') as BackFlushLoc,isnull(Reservable,'') Reservable, pass_req as PassReq,''as ExportDate,'' as DimensionUnits, 0 as Height,0 as Width, 0 as Depth, dock_time as DockToStock, isnull(feat_str,'') as 'Feature String','' as 'ItemType','' as Modvatable, '' as 'Design Source', '' as 'Mfg Part Number','' as 'Mfg Part Drawing Number', '' as 'Mfg Part Revision', '' as 'Sequencing Material', '' as 'Board Store Type', '' as 'Grained', ''as 'Supply Warehouse', '' as 'Supply Site', isnull(buyer,'') Buyer, isnull(setupgroup,'') as 'Setup Group' FROM material_extract as a INNER JOIN {Global.SytelineLiveDatabase}.dbo.item_mst on a.material = item INNER JOIN Site on site_ref = site.site where a.rowpointer ='{RowPointer}' and site.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_ExtractItemList.cs#25 — line 2019
```sql
SELECT Material, Description FROM dbo.Material_Extract WITH(NOLOCK) WHERE rowpointer = '{RowPointer}' AND live_status IS NULL AND ComponentFormula IS NULL UNION SELECT Material, Description FROM dbo.Material_Extract AS A WITH(NOLOCK) WHERE rowpointer = '{RowPointer}' AND live_status IS NULL AND ComponentFormula IS NOT NULL AND NOT EXISTS(SELECT 1 FROM Material_Extract AS B WHERE A.ComponentFormula = B.Material AND b.rowpointer = '{RowPointer}')
```

### BOM_ExtractItemList.cs#26 — line 2072
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'
```

### BOM_ExtractItemList.cs#27 — line 2123
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'
```

### BOM_ExtractItemList.cs#28 — line 2189
```sql
DELETE FROM dbo.Material_Extract WHERE rowpointer = '{RowPointer}'{, sqlConnection)}
```

### BOM_ExtractItemList.cs#29 — line 2292
```sql
SELECT DISTINCT Product.Product FROM Product WHERE Product.Product IN ( {text2} ) UNION SELECT DISTINCT Product.Product FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId WHERE Item.Item IN ({text2} ) ORDER BY Product.Product
```

## BOM_Manager.cs  (96)

### BOM_Manager.cs#1 — line 3323
```sql
SELECT Site, SL_LiveServer, SL_LiveDB, SL_TestServer, SL_TestDB FROM Site WHERE SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#2 — line 3437
```sql
exec Material_ItemLiveList '{Conversions.ToString(Global.catalogueId)}', '{Conversions.ToString(CurrentItemComboProductId)}', '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{) : (}select item.item, item.productid, product.name, 0 as islive from product inner join item on item.productid = product.productid where productrangeid in (select productrangeid from product where productid = {Conversions.ToString(CurrentItemComboProductId)}) and item.productid in (select item.productid from catalogueitems inner join item on item.itemid = catalogueitems.itemid where catalogueid = {Conversions.ToString(Global.catalogueId)} union select item.productid from CatalogueItemsUnreleased inner join item on item.itemid = CatalogueItemsUnreleased.itemid where catalogueid = {Conversions.ToString(Global.catalogueId)}) order by item.item{))}
```

### BOM_Manager.cs#3 — line 3517
```sql
select product.productid, product.name, product.productrangeid, product.product, productrange.productcategoryid, case when {text} = 0 then 0 else dbo.fnMaterial_IsLive( productrange.productcategoryid, product.productid, {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}) end as isLive from product inner join productrange On productrange.productrangeid = product.productrangeid where productid In ( Select distinct itemcomp.productid from item spitem inner join itemcomponents On itemcomponents.itemid = spitem.itemid inner join item itemcomp On itemcomp.itemid = itemcomponents.subitemid where spitem.productid = '{Conversions.ToString(CurrentItemComboProductId)}') order by product
```

### BOM_Manager.cs#4 — line 3598
```sql
select isnull(notes, '') notes, islive from MaterialProductId where MaterialProductId = '{Conversions.ToString(MaterialProductId)}'{, sqlConnection)}
```

### BOM_Manager.cs#5 — line 3610
```sql
select isnull(notes, '') notes, islive from MaterialProductId where MaterialProductId = '{Conversions.ToString(MaterialCommonProductId)}'
```

### BOM_Manager.cs#6 — line 3677
```sql
SELECT DISTINCT TOP 1 OperNum FROM MaterialData WHERE MaterialData.MaterialProductId = '{Conversions.ToString(MaterialProductId)}' ORDER BY OperNum{, sqlConnection)}
```

### BOM_Manager.cs#7 — line 3754
```sql
SELECT Material, Description FROM Material ORDER BY Material
```

### BOM_Manager.cs#8 — line 3835
```sql
Select cat.Name AS cataloguename, cpc.Name AS categoryname, pr.Name AS rangename FROM Product INNER JOIN ProductRange pr On Product.ProductRangeId = pr.ProductRangeId INNER JOIN CatalogueProductCategories cpc On pr.ProductCategoryId = cpc.ProductCategoryId AND cpc.CatalogueId = {Conversions.ToString(Global.catalogueId)} INNER JOIN Catalogue cat On cpc.CatalogueId = cat.CatalogueId WHERE Product.ProductId = {Conversions.ToString(CurrentProductId)}
```

### BOM_Manager.cs#9 — line 3845
```sql
Select atval.AttributeValueId, attr.Name, attr.Name + ' - ' + atval.Name AS NamePair, atval.productmaskvalue, attr.Attributeid, isnull(substring(atval.productmaskvalue, 0, charindex('|', atval.productmaskvalue)), '') as paravalue, attr.DisplayOrder, atval.DisplayOrdinal FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND (atval.OrderCodeValue IS NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) AND attr.DisplayOrder > 1) ) AND atval.attributevalueid IN (SELECT AttributeValueId FROM ProductAttributeValues WHERE ProductId = '{Conversions.ToString(CurrentProductId)}') AND atval.attributevalueid IN (SELECT AttributeValueId FROM CatalogueAttributeValues WHERE CatalogueId = '{Conversions.ToString(Global.catalogueId)}') ORDER BY attr.DisplayOrder, atval.DisplayOrdinal
```

### BOM_Manager.cs#10 — line 3867
```sql
SELECT Product FROM Product WHERE ProductId = {Conversions.ToString(CurrentProductId)}
```

### BOM_Manager.cs#11 — line 3876
```sql
SELECT distinct 0 as AttributeValueId, attr.Name, attr.Name AS NamePair, 'parametric' as 'productmaskvalue', attr.Attributeid, '' as paravalue, attr.DisplayOrder, 1 as DisplayOrdinal FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND attr.ProductCategoryId = '{Conversions.ToString(CurrentCategoryId)}' AND (atval.OrderCodeValue IS NOT NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) AND attr.DisplayOrder > 1) ) and atval.attributevalueid in (select attributevalueid from ProductAttributeValues where productid = '{Conversions.ToString(CurrentProductId)}') and atval.attributevalueid in (select attributevalueid from CatalogueAttributeValues where catalogueid = '{Conversions.ToString(Global.catalogueId)}') and productmaskvalue Is Not null union SELECT atval.AttributeValueId, attr.Name, attr.Name + ' - ' + atval.Name AS NamePair, atval.productmaskvalue, attr.Attributeid, isnull(substring(atval.productmaskvalue, 0, charindex('|', atval.productmaskvalue)), '') as paravalue,attr.DisplayOrder, atval.DisplayOrdinal FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND attr.ProductCategoryId = '{Conversions.ToString(CurrentCategoryId)}' AND (atval.OrderCodeValue IS NOT NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) AND attr.DisplayOrder > 1) ) and atval.attributevalueid in (select attributevalueid from ProductAttributeValues where productid = '{Conversions.ToString(CurrentProductId)}') and atval.attributevalueid in (select attributevalueid from CatalogueAttributeValues where catalogueid = '{Conversions.ToString(Global.catalogueId)}') and productmaskvalue Is null ORDER BY DisplayOrder, DisplayOrdinal
```

### BOM_Manager.cs#12 — line 3895
```sql
exec MaterialBOMOptions '{Product}', {Conversions.ToString(Global.catalogueId)}
```

### BOM_Manager.cs#13 — line 3910
```sql
SELECT atval.AttributeValueId,attr.Attributeid FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND attr.ProductCategoryId = {Conversions.ToString(CurrentCategoryId)} AND (atval.OrderCodeValue IS NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) AND attr.DisplayOrder > 1) ) and atval.attributevalueid in (select attributevalueid from ProductAttributeValues where productid in (select productid from product where productrangeid in (select ProductRangeId from ProductRange where ProductCategoryId in ( select ProductCategoryId from ProductRange where ProductRangeId =(select distinct productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}'))))) and atval.attributevalueid in (select attributevalueid from CatalogueAttributeValues where catalogueid = {Conversions.ToString(Global.catalogueId)})
```

### BOM_Manager.cs#14 — line 3920
```sql
SELECT distinct 0 as AttributeValueId, attr.Name, attr.Name AS NamePair, 'parametric' as 'productmaskvalue', attr.Attributeid, '' as paravalue, attr.DisplayOrder, 1 as DisplayOrdinal FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND attr.ProductCategoryId = '{Conversions.ToString(CurrentCategoryId)}' AND (atval.OrderCodeValue IS NOT NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) AND attr.DisplayOrder > 1) ) and atval.attributevalueid in (select attributevalueid from ProductAttributeValues where productid in (select productid from product where productrangeid in (select ProductRangeId from ProductRange where ProductCategoryId in ( select ProductCategoryId from ProductRange where ProductRangeId = (select distinct productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}'))))) and atval.attributevalueid in (select attributevalueid from CatalogueAttributeValues where catalogueid = '{Conversions.ToString(Global.catalogueId)}') and productmaskvalue Is Not null union SELECT atval.AttributeValueId, attr.Name, attr.Name + ' - ' + atval.Name AS NamePair, atval.productmaskvalue, attr.Attributeid, isnull(substring(atval.productmaskvalue, 0, charindex('|', atval.productmaskvalue)), '') as paravalue,attr.DisplayOrder, atval.DisplayOrdinal FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND attr.ProductCategoryId = '{Conversions.ToString(CurrentCategoryId)}' AND (atval.OrderCodeValue IS NOT NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) AND attr.DisplayOrder > 1) ) and atval.attributevalueid in (select attributevalueid from ProductAttributeValues where productid in (select productid from product where productrangeid in (select ProductRangeId from ProductRange where ProductCategoryId in ( select ProductCategoryId from ProductRange where ProductRangeId = (select distinct productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}'))))) and atval.attributevalueid in (select attributevalueid from CatalogueAttributeValues where catalogueid = '{Conversions.ToString(Global.catalogueId)}') and productmaskvalue Is null ORDER BY DisplayOrder, DisplayOrdinal
```

### BOM_Manager.cs#15 — line 3930
```sql
select distinct opt.OptionId,optval.OptionValueId from optionvalue optval inner join [option] opt on optval.optionid = opt.optionid inner join productcategory pc on opt.productcategoryid = pc.productcategoryid and (pc.productcategoryid = '{Conversions.ToString(CurrentCategoryId)}' or pc.productcategoryid = 1) -- global fabrics left outer join fabricbands fb on optval.optionvalueid = fb.optionvalueid and fb.application = 2 left outer join productoptionvalues pov0 on optval.optionvalueid = pov0.optionvalueid and pov0.productid in (select productid from product where productrangeid in ( select productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}')) --1st tier (dependentattributevalues) left outer join (select optval.optionvalueid, bav1.attributevalueid from optionvalue optval inner join dependentattributevalues dav1 on optval.optionvalueid = dav1.additionaloptionvalueid inner join baseattributevalues bav1 on dav1.attributevalueid = bav1.attributevalueid and bav1.itemid in (select itemid from item where productid in (select productid from product where productrangeid in ( select productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}'))) inner join attributevalue atval1 on dav1.attributevalueid = atval1.attributevalueid) as tier1 on optval.optionvalueid = tier1.optionvalueid -- 2nd tier (dependentattributevalues) left outer join (select optval.optionvalueid, bav2.attributevalueid, parent_optval2.optionid as pOptId, parent_opt2.descriptionid as pOptDescId, parent_opt2.name as pOptName, parent_optval2.optionvalueid as pOptValId, parent_optval2.descriptionid as pOptValDescId, parent_optval2.name as pOptValName, parent_optval2.ordercodevalue as pOptValCode, parent_opt2.isfabric as pOptFab, parent_opt2.displayorder as pOptDO from optionvalue optval inner join dependentoptionvalues dov2 on optval.optionvalueid = dov2.additionaloptionvalueid inner join optionvalue parent_optval2 on dov2.optionvalueid = parent_optval2.optionvalueid inner join [option] parent_opt2 on parent_optval2.optionid = parent_opt2.optionid inner join dependentattributevalues dav2 on dov2.optionvalueid = dav2.additionaloptionvalueid inner join baseattributevalues bav2 on dav2.attributevalueid = bav2.attributevalueid and bav2.itemid in (select itemid from item where productid in (select productid from product where productrangeid in ( select productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}'))) inner join attributevalue atval2 on dav2.attributevalueid = atval2.attributevalueid) as tier2 on optval.optionvalueid = tier2.optionvalueid -- 3rd tier (dependentattributevalues) left outer join (select optval.optionvalueid, bav3.attributevalueid, parent_optval3.optionid as pOptId, parent_opt3.descriptionid as pOptDescId, parent_opt3.name as pOptName, parent_optval3.optionvalueid as pOptValId, parent_optval3.descriptionid as pOptValDescId, parent_optval3.name as pOptValName, parent_optval3.ordercodevalue as pOptValCode, parent_opt3.isfabric as pOptFab, parent_opt3.displayorder as pOptDO from optionvalue optval inner join dependentoptionvalues dov3 on optval.optionvalueid = dov3.additionaloptionvalueid inner join optionvalue parent_optval3 on dov3.optionvalueid = parent_optval3.optionvalueid inner join [option] parent_opt3 on parent_optval3.optionid = parent_opt3.optionid inner join dependentoptionvalues dov3b on dov3.optionvalueid = dov3b.additionaloptionvalueid inner join dependentattributevalues dav3 on dov3b.optionvalueid = dav3.additionaloptionvalueid inner join baseattributevalues bav3 on dav3.attributevalueid = bav3.attributevalueid and bav3.itemid in (select itemid from item where productid in (select productid from product where productrangeid in ( select productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}'))) inner join attributevalue atval3 on dav3.attributevalueid = atval3.attributevalueid) as tier3 on optval.optionvalueid = tier3.optionvalueid -- 4th tier (dependentattributevalues) left outer join (select optval.optionvalueid, bav4.attributevalueid, parent_optval4.optionid as pOptId, parent_opt4.descriptionid as pOptDescId, parent_opt4.name as pOptName, parent_optval4.optionvalueid as pOptValId, parent_optval4.descriptionid as pOptValDescId, parent_optval4.name as pOptValName, parent_optval4.ordercodevalue as pOptValCode, parent_opt4.isfabric as pOptFab, parent_opt4.displayorder as pOptDO from optionvalue optval inner join dependentoptionvalues dov4 on optval.optionvalueid = dov4.additionaloptionvalueid inner join optionvalue parent_optval4 on dov4.optionvalueid = parent_optval4.optionvalueid inner join [option] parent_opt4 on parent_optval4.optionid = parent_opt4.optionid inner join dependentoptionvalues dov4b on dov4.optionvalueid = dov4b.additionaloptionvalueid inner join dependentoptionvalues dov4c on dov4b.optionvalueid = dov4c.additionaloptionvalueid inner join dependentattributevalues dav4 on dov4c.optionvalueid = dav4.additionaloptionvalueid inner join baseattributevalues bav4 on dav4.attributevalueid = bav4.attributevalueid and bav4.itemid in (select itemid from item where productid in (select productid from product where productrangeid in ( select productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}'))) inner join attributevalue atval4 on dav4.attributevalueid = atval4.attributevalueid) as tier4 on optval.optionvalueid = tier4.optionvalueid -- 5th tier (dependentoptionvalues) left outer join (select optval.optionvalueid, pov5.productid, optval5.optionid as pOptId, opt5.descriptionid as pOptDescId, opt5.name as pOptName, optval5.optionvalueid as pOptValId, optval5.descriptionid as pOptValDescId, optval5.name as pOptValName, optval5.ordercodevalue as pOptValCode, opt5.isfabric as pOptFab, opt5.displayorder as pOptDO from optionvalue optval inner join dependentoptionvalues dov5 on optval.optionvalueid = dov5.additionaloptionvalueid inner join productoptionvalues pov5 on dov5.optionvalueid = pov5.optionvalueid and pov5.productid in (select productid from product where productrangeid in ( select productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}')) inner join optionvalue optval5 on dov5.optionvalueid = optval5.optionvalueid inner join [option] opt5 on optval5.optionid = opt5.optionid) as tier5 on optval.optionvalueid = tier5.optionvalueid -- 6th tier (dependentoptionvalues) left outer join (select optval.optionvalueid, pov6.productid, optval6.optionid as pOptId, opt6.descriptionid as pOptDescId, opt6.name as pOptName, optval6.optionvalueid as pOptValId, optval6.descriptionid as pOptValDescId, optval6.name as pOptValName, optval6.ordercodevalue as pOptValCode, opt6.isfabric as pOptFab, opt6.displayorder as pOptDO from optionvalue optval inner join dependentoptionvalues dov6 on optval.optionvalueid = dov6.additionaloptionvalueid inner join dependentoptionvalues dov6b on dov6.optionvalueid = dov6b.additionaloptionvalueid inner join productoptionvalues pov6 on dov6b.optionvalueid = pov6.optionvalueid and pov6.productid in (select productid from product where productrangeid in ( select productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}')) inner join optionvalue optval6 on dov6.optionvalueid = optval6.optionvalueid inner join [option] opt6 on optval6.optionid = opt6.optionid) as tier6 on optval.optionvalueid = tier6.optionvalueid -- 7th tier (dependentoptionvalues) left outer join (select optval.optionvalueid, pov7.productid, optval7.optionid as pOptId, opt7.descriptionid as pOptDescId, opt7.name as pOptName, optval7.optionvalueid as pOptValId, optval7.descriptionid as pOptValDescId, optval7.name as pOptValName, optval7.ordercodevalue as pOptValCode, opt7.isfabric as pOptFab, opt7.displayorder as pOptDO from optionvalue optval inner join dependentoptionvalues dov7 on optval.optionvalueid = dov7.additionaloptionvalueid inner join dependentoptionvalues dov7b on dov7.optionvalueid = dov7b.additionaloptionvalueid inner join dependentoptionvalues dov7c on dov7b.optionvalueid = dov7c.additionaloptionvalueid inner join productoptionvalues pov7 on dov7c.optionvalueid = pov7.optionvalueid and pov7.productid in (select productid from product where productrangeid in ( select productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}')) inner join optionvalue optval7 on dov7.optionvalueid = optval7.optionvalueid inner join [option] opt7 on optval7.optionid = opt7.optionid) as tier7 on optval.optionvalueid = tier7.optionvalueid -- 8th tier (dependentoptionvalues) left outer join (select optval.optionvalueid, pov8.productid, optval8.optionid as pOptId, opt8.descriptionid as pOptDescId, opt8.name as pOptName, optval8.optionvalueid as pOptValId, optval8.descriptionid as pOptValDescId, optval8.name as pOptValName, optval8.ordercodevalue as pOptValCode, opt8.isfabric as pOptFab, opt8.displayorder as pOptDO from optionvalue optval inner join dependentoptionvalues dov8 on optval.optionvalueid = dov8.additionaloptionvalueid inner join dependentoptionvalues dov8b on dov8.optionvalueid = dov8b.additionaloptionvalueid inner join dependentoptionvalues dov8c on dov8b.optionvalueid = dov8c.additionaloptionvalueid inner join dependentoptionvalues dov8d on dov8c.optionvalueid = dov8d.additionaloptionvalueid inner join productoptionvalues pov8 on dov8d.optionvalueid = pov8.optionvalueid and pov8.productid in (select productid from product where productrangeid in ( select productrangeid from product where productid = '{Conversions.ToString(CurrentProductId)}')) inner join optionvalue optval8 on dov8.optionvalueid = optval8.optionvalueid inner join [option] opt8 on optval8.optionid = opt8.optionid) as tier8 on optval.optionvalueid = tier8.optionvalueid where pov0.optionvalueid is not null or (tier1.optionvalueid is not null and tier1.attributevalueid is not null) or (tier2.optionvalueid is not null and tier2.attributevalueid is not null) or (tier3.optionvalueid is not null and tier3.attributevalueid is not null) or (tier4.optionvalueid is not null and tier4.attributevalueid is not null) or (tier5.optionvalueid is not null and tier5.productid is not null) or (tier6.optionvalueid is not null and tier6.productid is not null) or (tier7.optionvalueid is not null and tier7.productid is not null) or (tier8.optionvalueid is not null and tier8.productid is not null)
```

### BOM_Manager.cs#16 — line 4188
```sql
SELECT ProductMaskValue FROM AttributeValue WHERE AttributeId = {Conversions.ToString(attrId)}
```

### BOM_Manager.cs#17 — line 4399
```sql
select material from material where materialid = '{array[1]}'
```

### BOM_Manager.cs#18 — line 4784
```sql
select 1 from MaterialSubjob where SubJobMaterialId = {SubJobMaterialId} and ISNULL(OperNum,10) = {Conversions.ToString(sendOperNum)} and MaterialId = {MaterialId} and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#19 — line 4792
```sql
UPDATE MaterialSubjob SET deletestatus = 0, Formula = '{Formula.ToUpper().Replace(} {,}{)}', ObsDate = @ObsDate, EffectiveDate = @EffectDate, ScrapFactor = '{ScrapFactor.ToUpper().Replace(} {,}{)}', RGID = '{sendRGID}', OperNum = {Conversions.ToString(sendOperNum)} WHERE SubJobMaterialId = {SubJobMaterialId} and MaterialId = {MaterialId} and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' ~UPDATE MaterialSubjob SET FamilyCode = '{sendFamilycode}' where SubJobMaterialId = {SubJobMaterialId} and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#20 — line 4797
```sql
INSERT INTO MaterialSubjob (SubJobMaterialId, MaterialId, Formula, SiteId, Scrapfactor, EffectiveDate, ObsDate, IsSubJob,FamilyCode,RGID,OperNum) VALUES ({SubJobMaterialId}, {MaterialId}, '{Formula.ToUpper().Replace(} {,}{)}', '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}', '{ScrapFactor.ToUpper().Replace(} {,}{)}', @EffectDate, @ObsDate, '{Conversions.ToString(num)}','{sendFamilycode}','{sendRGID}','{Conversions.ToString(sendOperNum)}')
```

### BOM_Manager.cs#21 — line 4861
```sql
select MaterialId, Material from Material where Material = '{sendItem.Replace(} {,}{)}'{, sqlConnection)}
```

### BOM_Manager.cs#22 — line 4866
```sql
insert into Material (Material, Description) values ('{sendItem.Replace(} {,}{)}', N'{sendDescription.Replace(}'{,}''{)}')
```

### BOM_Manager.cs#23 — line 4869
```sql
select MaterialId, Material from Material where Material = '{sendItem.Replace(} {,}{)}'
```

### BOM_Manager.cs#24 — line 4908
```sql
SELECT item FROM item WITH(NOLOCK) WHERE stat = 'A' AND item = '{sendItem}'
```

### BOM_Manager.cs#25 — line 4911
```sql
SELECT item FROM item_mst WITH(NOLOCK) WHERE stat = 'A' AND item = '{sendItem}' AND site_ref = '{Global.SytelineSite}'
```

### BOM_Manager.cs#26 — line 4954
```sql
SELECT Item, Description FROM Item WHERE Item = '{MaterialString}'
```

### BOM_Manager.cs#27 — line 4957
```sql
SELECT Item, Description FROM item_mst WHERE item = '{MaterialString}' AND site_ref = '{Global.SytelineSite}'
```

### BOM_Manager.cs#28 — line 4983
```sql
SELECT Item, Description FROM Item WHERE Item = '{MaterialString}'
```

### BOM_Manager.cs#29 — line 4986
```sql
SELECT Item, Description FROM item_mst WHERE item = '{MaterialString}' AND site_ref = '{Global.SytelineSite}'
```

### BOM_Manager.cs#30 — line 5041
```sql
select ordercodevalue from optionvalue where optionvalueid = '{NameOptionId}'
```

### BOM_Manager.cs#31 — line 5092
```sql
insert into MaterialCriteria (categoryid, attributevalueids, optionvalueids) values ('{Conversions.ToString(CurrentCategoryId)}', '{AttributeValues}', '{Options}')
```

### BOM_Manager.cs#32 — line 5096
```sql
select MaterialCriteriaId from MaterialCriteria where isnull(attributevalueids, '') = '{AttributeValues}' and isnull(optionvalueids, '') = '{Options}' and categoryid = '{Conversions.ToString(CurrentCategoryId)}'
```

### BOM_Manager.cs#33 — line 5130
```sql
SELECT MaterialDataId FROM MaterialData WHERE MaterialCriteriaId = {Conversions.ToString(CriteriaId)} AND MaterialId = {Conversions.ToString(MaterialId)} AND SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))} AND MaterialProductId = {Conversions.ToString(sendMaterialProdId)} AND OperNum = '{OperNum}' AND IsSubJob = {Conversions.ToString(num)}
```

### BOM_Manager.cs#34 — line 5138
```sql
INSERT INTO MaterialData (MaterialCriteriaId, MaterialId, MaterialProductId, OperNum, Formula, SiteId, IsSubJob, ScrapFactor, EffectiveDate, ObsDate, RGID, IsOperCriteria) VALUES ({Conversions.ToString(CriteriaId)}, {Conversions.ToString(MaterialId)}, {Conversions.ToString(sendMaterialProdId)}, '{OperNum}', '{Formula.ToUpper().Replace(} {,}{).Replace(}'{,}''{)}', {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}, {Conversions.ToString(num)}, '{ScrapFactor}', @EffectDate, @ObsDate, '{sendRGID}', {Conversions.ToString(IsOperCriteria)}); SELECT @@IDENTITY
```

### BOM_Manager.cs#35 — line 5141
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### BOM_Manager.cs#36 — line 5144
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### BOM_Manager.cs#37 — line 5153
```sql
INSERT INTO PDMAudit.dbo.BOMUpdates (TransactionId, MaterialProductId, MaterialSubJobId, MaterialId, [Key], PrevValue, NewValue, SiteId, ActionTaken) VALUES ({Conversions.ToString(num3)}, {Conversions.ToString(sendMaterialProdId)}, NULL, {Conversions.ToString(MaterialId)}, 'New Operation', NULL, '{OperNum}', {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}, 'Insert')
```

### BOM_Manager.cs#38 — line 5164
```sql
UPDATE MaterialData Set DeleteStatus = 0, Formula = '{Formula.ToUpper().Replace(} {,}{).TrimStart('=')
 .Replace(}'{,}''{)}', ScrapFactor = '{ScrapFactor.ToUpper().Replace(} {,}{)}', EffectiveDate = @EffectDate, ObsDate = @ObsDate, RGID = '{sendRGID}', IsOperCriteria = {Conversions.ToString(IsOperCriteria)}WHERE MaterialDataId = {Conversions.ToString(num4)}
```

### BOM_Manager.cs#39 — line 5291
```sql
select description from material where material = '{material_combo.Text}'
```

### BOM_Manager.cs#40 — line 5347
```sql
exec dbo.Material_LoadTree '{Conversions.ToString(MaterialProdId)}', '{Conversions.ToString(CurrentCategoryId)}', '{Conversions.ToString(CurrentProductId)}', '{Conversions.ToString(Global.catalogueId)}', '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}', '{Conversions.ToString(DeleteStatus)}', '{Conversions.ToString(num)}', '{Product}'
```

### BOM_Manager.cs#41 — line 5549
```sql
SELECT DISTINCT curMatSubJob.MaterialId, Material, Description, curMatSubJob.Formula, curMatSubJob.EffectiveDate, curMatSubJob.ObsDate, curMatSubJob.ScrapFactor,curMatSubJob.IsSubJob,curMatSubJob.deletestatus, ISNULL(curMatSubJob.OperNum,10) AS OperNum,curfcrg.OperDesc,ISNULL(nextMatSubJob.FamilyCode,'') as FamilyCode,nextfcrg.FamilyCodeDesc FROM MaterialSubJob AS curMatSubJob WITH(NOLOCK) LEFT OUTER JOIN MaterialSubJob AS nextMatSubJob WITH(NOLOCK) ON curMatSubJob.materialid = nextMatSubJob.SubjobMaterialId INNER JOIN Material WITH(NOLOCK) ON curMatSubJob.materialid = material.materialid LEFT OUTER JOIN FamCodeResourceGroup AS curfcrg WITH(NOLOCK) ON curMatSubJob.SiteId = curfcrg.siteid And curMatSubJob.FamilyCode = curfcrg.FamilyCode And curMatSubJob.OperNum = curfcrg.OperNum LEFT OUTER JOIN FamCodeResourceGroup AS nextfcrg WITH(NOLOCK) ON curMatSubJob.SiteId = nextfcrg.siteid And nextMatSubJob.FamilyCode = nextfcrg.FamilyCode And nextMatSubJob.OperNum = nextfcrg.OperNum WHERE curMatSubJob.SubjobMaterialId = '{SubJobMaterialId}' AND curMatSubJob.SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#42 — line 5692
```sql
delete from materialdata from materialdata inner join material on materialdata.materialid = material.materialid where materialcriteriaid = '{Conversions.ToString(CriteriaId)}' and material.materialid = '{Conversions.ToString(MaterialId)}' and materialdata.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and materialproductid = '{Conversions.ToString(sendMaterialProductId)}' and OperNum = '{Conversions.ToString(OperNum)}'
```

### BOM_Manager.cs#43 — line 5762
```sql
SELECT top 1 ISNULL(materialproductid.Familycode,'') as Familycode, ISNULL(materialdata.OperNum,{array[0]}) as OperNum,ISNULL(IsOperCriteria ,0) as IsOperCriteria from materialdata inner join materialproductid on materialdata.siteid = materialproductid.siteid AND materialdata.materialproductid = materialproductid.materialproductid left outer join FamCodeResourceGroup AS fcrg with(nolock) on materialproductid.siteid = fcrg.siteid AND materialproductid.FamilyCode = fcrg.FamilyCode and materialdata.opernum = fcrg.OperNum where materialdata.siteid = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))} AND materialdata.materialproductid = '{text}' and
```

### BOM_Manager.cs#44 — line 5789
```sql
SELECT top 1 ISNULL(materialsubjob.Familycode,'') as Familycode, ISNULL(materialsubjob.OperNum,{array[0]}) as OperNum,0 AS IsOperCriteria from materialsubjob with(nolock) left outer join FamCodeResourceGroup AS fcrg with(nolock) on materialsubjob.siteid = fcrg.siteid AND materialsubjob.FamilyCode = fcrg.FamilyCode and materialsubjob.opernum = fcrg.OperNum WHERE materialsubjob.siteid = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))} AND materialsubjob.SubJobMaterialId = '{array4[1]}' AND materialsubjob.OperNum = {array[0]}
```

### BOM_Manager.cs#45 — line 5812
```sql
SELECT top 1 ISNULL(materialsubjob.Familycode,'') as Familycode, ISNULL(materialsubjob.OperNum,{array[0]}) as OperNum,0 AS IsOperCriteria from materialsubjob with(nolock) WHERE materialsubjob.SubJobMaterialId = '{array[1]}' AND siteid = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))} AND deletestatus = 0
```

### BOM_Manager.cs#46 — line 5818
```sql
SELECT top 1 ISNULL(materialsubjob.Familycode,'') as Familycode, ISNULL(materialsubjob.OperNum,{array[0]}) as OperNum,0 AS IsOperCriteria from materialsubjob with(nolock) WHERE materialsubjob.SubJobMaterialId = '{array6[1]}' and materialsubjob.issubjob = 0 AND siteid = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))} AND deletestatus = 0 and materialsubjob.opernum = {array[0]}
```

### BOM_Manager.cs#47 — line 5975
```sql
select productid from item where item = '{copyitem_combobox.Text}'
```

### BOM_Manager.cs#48 — line 6112
```sql
SELECT TOP 1 SubJobMaterialId, FamilyCode, RGID, ISNULL(OperNum,10) AS OperNum FROM MaterialSubjob AS ms WITH(NOLOCK) WHERE ms.SubJobMaterialId = '{array2[1]}' AND ISNULL(OperNum,10) = '{text3}'
```

### BOM_Manager.cs#49 — line 6184
```sql
delete from MaterialSubJob where SubjobMaterialId = '{array3[1]}' and MaterialId = '{array4[1]}' and ISNULL(OperNum,10) = '{array4[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{, sqlConnection)}
```

### BOM_Manager.cs#50 — line 6248
```sql
select isnull(attributevalueids, '') as attributevalueids, isnull(optionvalueids, '') as optionvalueids from materialcriteria where materialcriteriaid = '{array8[0]}' and categoryid = '{Conversions.ToString(CurrentCategoryId)}'
```

### BOM_Manager.cs#51 — line 6314
```sql
SELECT TOP 1 SubJobMaterialId, FamilyCode, RGID, ISNULL(OperNum,10) AS OperNum FROM MaterialSubjob AS ms WITH(NOLOCK) WHERE ms.SubJobMaterialId = '{array12[1]}' AND SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' ORDER BY opernum
```

### BOM_Manager.cs#52 — line 6354
```sql
select material, effectivedate, obsdate, scrapfactor, formula from materialdata inner join material on material.materialid = materialdata.materialid where materialdataid = '{array12[2]}'
```

### BOM_Manager.cs#53 — line 6492
```sql
select isnull(attributevalueids, '') as attributevalueids, isnull(optionvalueids, '') as optionvalueids from materialcriteria where materialcriteriaid = '{text2}' and categoryid = '{Conversions.ToString(CurrentCategoryId)}'
```

### BOM_Manager.cs#54 — line 6616
```sql
SELECT DISTINCT Product.ProductId, Product.Product, Product.Name FROM Product INNER JOIN Item On Product.ProductId = Item.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId LEFT OUTER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId WHERE pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND itco.ItemId IS NULL /* NOT a super product */ UNION SELECT DISTINCT Product.ProductId, Product.Product, Product.Name FROM Product INNER JOIN Item On Product.ProductId = Item.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId INNER JOIN CatalogueItemsUnreleased ciu ON Item.ItemId = ciu.ItemId LEFT OUTER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId WHERE pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND itco.ItemId IS NULL /* NOT a super product */ ORDER BY Product.Product
```

### BOM_Manager.cs#55 — line 6745
```sql
select top 1 attributevalueids from materialcriteria where materialcriteriaid = {text}
```

### BOM_Manager.cs#56 — line 6751
```sql
select attribute.attributeid, attribute.[Name] as NamePair, attributevalue.attributevalueid, attributevalue.[Name] from dbo.fnhm_split('{, sqlDataReader[}attributevalueids{]),}', '|') att inner join {),}attributevalue on attributevalue.attributevalueid = att.data inner join {),}attribute on attribute.attributeid = attributevalue.attributeid {),}order by attribute.displayorder{))}
```

### BOM_Manager.cs#57 — line 6782
```sql
select top 1 optionvalueids from materialcriteria where materialcriteriaid = {text}
```

### BOM_Manager.cs#58 — line 6788
```sql
select [option].optionid, [option].[name] as optname, [option].displayorder, [optionvalue].optionvalueid, [optionvalue].[name], [optionvalue].ordercodevalue from dbo.fnhm_split('{, sqlDataReader[}optionvalueids{]),}', '|') opt inner join {),}optionvalue on optionvalue.optionvalueid = opt.[data] inner join {),}[option] on [option].optionid = optionvalue.optionid {),}order by [option].displayorder{))}
```

### BOM_Manager.cs#59 — line 6917
```sql
select material, effectivedate, obsdate, scrapfactor, formula from materialdata inner join material on material.materialid = materialdata.materialid where materialdataid = '{array[1]}'
```

### BOM_Manager.cs#60 — line 6922
```sql
select effectivedate, obsdate from materialsubjob where subjobmaterialid = '{array3[1]}' and materialid = '{array[1]}' and ISNULL(OperNum,10) = '{array[0]}' and siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#61 — line 6945
```sql
select top 1 SubJobMaterialId,FamilyCode,RGID,ISNULL(OperNum,10) AS OperNum from MaterialSubjob as ms WITH(NOLOCK) where ms.SubJobMaterialId = '{array2[1]}' and siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#62 — line 7478
```sql
update materialdata set formula = '{replace_with_combo.Text.ToUpper().Replace(} {,}{)}' where materialdataid = '{text2}' and siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#63 — line 7497
```sql
update materialsubjob set formula = '{replace_with_combo.Text.ToUpper().Replace(} {,}{)}' where subjobmaterialid = '{array3[1]}' and materialid = '{array2[1]}' and ISNULL(OperNum,10) = '{array2[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#64 — line 7515
```sql
update materialsubjob set formula = '{replace_with_combo.Text.ToUpper().Replace(} {,}{)}' where subjobmaterialid = '{array4[2]}' and materialid = '{array4[1]}' and ISNULL(OperNum,10) = '{array4[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#65 — line 7609
```sql
select top 1 SubJobMaterialId,FamilyCode,RGID,ISNULL(OperNum,10) AS OperNum from MaterialSubjob as ms WITH(NOLOCK) where ms.SubJobMaterialId = '{array3[1]}' and ISNULL(OperNum,10) = '{array2[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#66 — line 7690
```sql
delete from materialdata from materialdata inner join material on materialdata.materialid = material.materialid where materialcriteriaid = '{Conversions.ToString(CriteriaId)}' and material.materialid = '{Conversions.ToString(MaterialId)}' and materialdata.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and materialproductid = '{Conversions.ToString(MaterialProductId)}' and OperNum = '{Conversions.ToString(OperNum)}'
```

### BOM_Manager.cs#67 — line 7728
```sql
delete from MaterialSubJob where SubjobMaterialId = '{array2[1]}' and MaterialId = '{array[1]}' and ISNULL(OperNum,10) = '{array[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{, sqlConnection)}
```

### BOM_Manager.cs#68 — line 7815
```sql
update materialdata set formula = '{replace_with_combo.Text.ToUpper().Replace(} {,}{)}' where materialdataid = '{text2}' and siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#69 — line 7834
```sql
update materialsubjob set formula = '{replace_with_combo.Text.ToUpper().Replace(} {,}{)}' where subjobmaterialid = '{array3[1]}' and materialid = '{array2[1]}' and ISNULL(OperNum,10) = '{array2[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#70 — line 7852
```sql
update materialsubjob set formula = '{replace_with_combo.Text.ToUpper().Replace(} {,}{)}' where subjobmaterialid = '{array4[2]}' and materialid = '{array4[1]}' and ISNULL(OperNum,10) = '{array4[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#71 — line 7855
```sql
update materialsubjob set formula = '{formula_textbox.Text.ToUpper().Replace(} {,}{)}', effectivedate = @effdate, obsdate = @obsdate, scrapfactor = '{scrapfactor_textbox.Text.ToUpper().Replace(} {,}{)}' where subjobmaterialid = '{array4[2]}' and materialid = '{array4[1]}' and ISNULL(OperNum,10) = '{array4[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#72 — line 7927
```sql
select top 1 SubJobMaterialId,FamilyCode,RGID,ISNULL(OperNum,10) AS OperNum from MaterialSubjob as ms WITH(NOLOCK) where ms.SubJobMaterialId = '{array3[1]}' and ISNULL(OperNum,10) = '{array2[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_Manager.cs#73 — line 7982
```sql
update materialproductid set islive = '{text}' where materialproductid = '{Conversions.ToString(MaterialProductId)}'{, sqlConnection)}
```

### BOM_Manager.cs#74 — line 8033
```sql
update materialproductid set islive = '{text}' where materialproductid = '{Conversions.ToString(MaterialCommonProductId)}'{, sqlConnection)}
```

### BOM_Manager.cs#75 — line 8075
```sql
update MaterialProductId set notes = '{ProductNotesTextBox.Text.Replace(}'{,}''{)}' where MaterialProductId = '{Conversions.ToString(MaterialProductId)}'{, sqlConnection)}
```

### BOM_Manager.cs#76 — line 8078
```sql
update MaterialProductId set notes = '{CommonNotesTextBox.Text.Replace(}'{,}''{)}' where MaterialProductId = '{Conversions.ToString(MaterialCommonProductId)}'
```

### BOM_Manager.cs#77 — line 8112
```sql
SELECT DISTINCT MaterialId, SiteId FROM MaterialData WHERE MaterialCriteriaId = {Conversions.ToString(matlCriteriaId)} AND (MaterialProductId = {Conversions.ToString(matlProductId)} OR MaterialProductId = {Conversions.ToString(matlCommProductId)}) AND DeleteStatus = 0
```

### BOM_Manager.cs#78 — line 8125
```sql
SELECT Material FROM Material WHERE MaterialId IN (
```

### BOM_Manager.cs#79 — line 8220
```sql
SELECT fcrg.Familycode, fcrg.Rgid,fcrg.OperNum FROM DBO.MaterialProductId WITH(NOLOCK) INNER JOIN DBO.FamCodeResourceGroup AS fcrg WITH(NOLOCK) ON MaterialProductId.Siteid = fcrg.Siteid And MaterialProductId.FamilyCode = fcrg.FamilyCode WHERE MaterialProductId.SiteId= '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND MaterialProductId = {Conversions.ToString(MaterialProductId)} ORDER BY fcrg.operNum
```

### BOM_Manager.cs#80 — line 8330
```sql
EXEC MaterialBOM_RawMaterialExport '{Conversions.ToString(MaterialProductId)}','{Conversions.ToString(MaterialCommonProductId)}'
```

### BOM_Manager.cs#81 — line 8470
```sql
SELECT fcrg.Familycode, fcrg.Rgid,fcrg.OperNum FROM DBO.MaterialProductId wITH(NOLOCK) INNER JOIN DBO.FamCodeResourceGroup AS fcrg WITH(NOLOCK) ON MaterialProductId.Siteid = fcrg.Siteid And MaterialProductId.FamilyCode = fcrg.FamilyCode WHERE MaterialProductId.SiteId= '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND MaterialProductId = {Conversions.ToString(MaterialProductId)} ORDER BY fcrg.operNum
```

### BOM_Manager.cs#82 — line 8644
```sql
SELECT fcrg.Familycode, fcrg.Rgid,fcrg.OperNum FROM DBO.FamCodeResourceGroup as fcrg WITH(NOLOCK) WHERE fcrg.SiteId= '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND fcrg.Familycode = '{text3}' ORDER BY fcrg.operNum
```

### BOM_Manager.cs#83 — line 8966
```sql
EXEC Material_FamilyCode_Verification '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}','{Conversions.ToString(MaterialProductId)}','{Conversions.ToString(MaterialCommonProductId)}'
```

### BOM_Manager.cs#84 — line 8994
```sql
EXEC Material_Formula_Verification '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}', '{Conversions.ToString(Global.catalogueId)}', '{Conversions.ToString(Global.categoryId)}', '{Conversions.ToString(MaterialProductId)}', '{Conversions.ToString(MaterialCommonProductId)}', '{Conversions.ToString(Global.productId)}', '{Product}'
```

### BOM_Manager.cs#85 — line 9097
```sql
Select OrderCodeValue, attr.Name, attr.Name As NamePair, productmaskvalue, attr.Attributeid, attr.DisplayOrder, DisplayOrdinal FROM AttributeValue atval INNER JOIN Attribute attr On atval.AttributeId = attr.AttributeId WHERE Status = 1 And attr.ProductCategoryId = '{Conversions.ToString(CurrentCategoryId)}' AND (atval.OrderCodeValue IS NOT NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) AND attr.DisplayOrder > 1) ) and atval.attributevalueid in (select attributevalueid from ProductAttributeValues where productid = '{Conversions.ToString(CurrentProductId)}') and atval.attributevalueid in (select attributevalueid from CatalogueAttributeValues where catalogueid = '{Conversions.ToString(Global.catalogueId)}') and productmaskvalue Is Not null and atval.Attributeid = '{, _physattid[phys_atvals_listbox.SelectedIndex]),}' ORDER BY DisplayOrdinal {))}
```

### BOM_Manager.cs#86 — line 9131
```sql
SELECT OrderCodeValue, attr.Name, attr.Name AS NamePair, productmaskvalue, attr.Attributeid, attr.DisplayOrder, DisplayOrdinal FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND attr.ProductCategoryId = '{Conversions.ToString(CurrentCategoryId)}' AND (atval.OrderCodeValue IS NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) AND attr.DisplayOrder > 1) ) and atval.attributevalueid in (select attributevalueid from ProductAttributeValues where productid = '{Conversions.ToString(CurrentProductId)}') and atval.attributevalueid in (select attributevalueid from CatalogueAttributeValues where catalogueid = '{Conversions.ToString(Global.catalogueId)}') and productmaskvalue Is Not null and atval.Attributeid = '{, _funcattid[func_atvals_listbox.SelectedIndex]),}' ORDER BY DisplayOrdinal {))}
```

### BOM_Manager.cs#87 — line 9173
```sql
SELECT FamilyCode, FamilyCodeDesc, OperNum, QtyResources, RGIDDesc,WC,CntrlPoint, RunMchHrs,Runlbrhrs FROM FamCodeResourceGroup WITH(NOLOCK) WHERE SiteID = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}
```

### BOM_Manager.cs#88 — line 9265
```sql
SELECT DISTINCT FamilyCode, familyCodeDesc as 'Description' FROM FamCodeResourceGroup WITH(NOLOCK) WHERE Siteid = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))} ORDER BY FamilyCode
```

### BOM_Manager.cs#89 — line 9320
```sql
SELECT ISNULL(FamilyCode,'') as 'FamilyCode' FROM dbo.MaterialProductid AS A WITH(NOLOCK) WHERE Siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' And MaterialProductId = '{sendMaterialProductid}'
```

### BOM_Manager.cs#90 — line 9354
```sql
SELECT DISTINCT RGID, OperNum , CAST(OperNum AS VARCHAR(4)) +'--'+ OperDesc as OperDesc FROM FamCodeResourceGroup WITH(NOLOCK) WHERE siteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))} And FamilyCode = '{familyCode_combox.SelectedValue.ToString().Trim()}' ORDER BY OperNum
```

### BOM_Manager.cs#91 — line 9418
```sql
select ISNULL(FamilyCode,'') as FamilyCode from materialproductid where materialproductid = '{Conversions.ToString(MaterialProductIdTemp)}'{) : (}select top 1 ISNULL(FamilyCode,'') as FamilyCode from materialsubjob where SubJobMaterialId = '{Conversions.ToString(MaterialProductIdTemp)}' and materialsubjob.Siteid ='{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and materialsubjob.DeleteStatus = 0 {))}
```

### BOM_Manager.cs#92 — line 9434
```sql
EXEC dbo.sp_SetupFamilyCodeForMaterialProductid {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}, '{Conversions.ToString(MaterialProductIdTemp)}','{sendFamilyCode}','{Conversions.ToString(num)}'
```

### BOM_Manager.cs#93 — line 9464
```sql
SELECT TOP 1 MaterialData.RGID,ISNULL(MaterialData.IsOperCriteria,0) AS IsOperCriteria FROM DBO.Materialdata WITH(NOLOCK) INNER JOIN DBO.MaterialProductId AS mp WITH(NOLOCK) ON MaterialData.materialproductid = mp.MaterialProductid LEFT OUTER JOIN DBO.FamCodeResourceGroup AS fcrg WITH(NOLOCK) ON mp.Siteid = fcrg.Siteid AND mp.FamilyCode = fcrg.FamilyCode AND Materialdata.OperNum = fcrg.OperNum WHERE Materialdata.SiteId= '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND Materialdata.MaterialProductId = {MaterialProductid} AND Materialdata.OperNum = '{Conversions.ToString(OperNum)}' AND Materialdata.DeleteStatus = 0
```

### BOM_Manager.cs#94 — line 9476
```sql
SELECT top 1 fcrg.RGID,0 AS IsOperCriteria FROM DBO.MaterialProductId AS mp WITH(NOLOCK) LEFT OUTER JOIN DBO.FamCodeResourceGroup AS fcrg WITH(NOLOCK) ON mp.Siteid = fcrg.Siteid And mp.FamilyCode = fcrg.FamilyCode WHERE mp.SiteId= '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND mp.MaterialProductId = {MaterialProductid} AND fcrg.OperNum = '{Conversions.ToString(OperNum)}'
```

### BOM_Manager.cs#95 — line 9508
```sql
SELECT 1 FROM materialdata AS md WITH(NOLOCK) INNER JOIN materialproductid AS mp WITH(NOLOCK) ON md.materialproductid = mp.materialproductid INNER JOIN dbo.FamCodeResourceGroup AS fcrg WITH(NOLOCK) ON mp.siteid = fcrg.siteid and mp.FamilyCode = fcrg.FamilyCode and md.rgid = fcrg.rgid and md.OperNum = fcrg.OperNum WHERE md.Siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND md.materialproductid = '{sendmaterialproductid}' AND md.operNum = '{sendoperNum}'{) : (}SELECT 1 FROM DBO.materialsubjob WITH(NOLOCK) INNER JOIN dbo.FamCodeResourceGroup as fcrg with(nolock) ON materialsubjob.siteid = fcrg.siteid AND materialsubjob.FamilyCode = fcrg.FamilyCode AND materialsubjob.OperNum = fcrg.OperNum AND materialsubjob.rgid = fcrg.rgid WHERE materialsubjob.Siteid ='{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND materialsubjob.SubJobMaterialId = '{sendmaterialproductid}' AND materialsubjob.OperNum = '{sendoperNum}'{))}
```

### BOM_Manager.cs#96 — line 9535
```sql
SELECT 1 FROM materialdata WITH(NOLOCK) WHERE Siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND materialproductid = '{sendmaterialproductid}' AND operNum = '{sendoperNum}' AND DeleteStatus = 0 AND ISNULL(isOperCriteria,0) <> '{Conversions.ToString(IsOperCriteria)}'
```

## BOM_MaterialTreeMenu.cs  (27)

### BOM_MaterialTreeMenu.cs#1 — line 913
```sql
select Formula, Material, description, isnull(scrapfactor, 0) as scrapfactor, effectivedate, obsdate, isnull(pip_sequence, 0) as pip_sequence, isnull(pip_page, 1) as pip_page from materialdata inner join material on material.materialid = materialdata.materialid where materialdataid = '{text}' and siteid = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}
```

### BOM_MaterialTreeMenu.cs#2 — line 919
```sql
select Formula, Material, description, isnull(scrapfactor, 0) as scrapfactor, effectivedate, obsdate, isnull(pip_sequence, 0) as pip_sequence, isnull(pip_page, 1) as pip_page from MaterialSubJob inner join material on material.materialid = materialsubjob.materialid where subjobmaterialid = '{array3[1]}' And MaterialSubJob.materialid = '{array2[1]}' And ISNULL(MaterialSubJob.opernum,10) = '{array2[0]}' and MaterialSubJob.siteid = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}
```

### BOM_MaterialTreeMenu.cs#3 — line 924
```sql
select Formula, Material, description, isnull(scrapfactor, 0) as scrapfactor, effectivedate, obsdate, isnull(pip_sequence, 0) as pip_sequence, isnull(pip_page, 1) as pip_page from materialsubjob inner join material on material.materialid = materialsubjob.materialid where materialsubjob.subjobmaterialid = '{array4[2]}' And materialsubjob.materialid = '{array4[1]}' And ISNULL(materialsubjob.opernum,10) = '{array4[0]}' and MaterialSubJob.siteid = {Conversions.ToString(Global.SiteId(allowPLCOverride: false))}
```

### BOM_MaterialTreeMenu.cs#4 — line 990
```sql
update materialsubjob set deletestatus = 1 from materialsubjob where materialsubjob.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and SubJobMaterialId = '{array[1]}' and ISNULL(OperNum,10) = '{text}'
```

### BOM_MaterialTreeMenu.cs#5 — line 994
```sql
update materialdata set deletestatus = 1 from materialdata where materialdata.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and materialproductid = '{Conversions.ToString(SetMaterialProductId)}' and OperNum = '{text}'
```

### BOM_MaterialTreeMenu.cs#6 — line 1038
```sql
update materialdata set deletestatus = 1 from materialdata inner join material on materialdata.materialid = material.materialid where materialcriteriaid = '{text2}' and materialdata.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and materialproductid = '{Conversions.ToString(SetMaterialProductId)}' and OperNum = '{text}'
```

### BOM_MaterialTreeMenu.cs#7 — line 1124
```sql
update materialsubjob set deletestatus = 1 from materialsubjob where subjobmaterialid = '{array5[2]}' and materialid = '{array5[1]}' and ISNULL(opernum,10) = '{array5[0]}' and issubjob = 1 and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{, sqlConnection)}
```

### BOM_MaterialTreeMenu.cs#8 — line 1138
```sql
update materialsubjob set deletestatus = 1 from MaterialSubJob where SubjobMaterialId = '{array6[1]}' and MaterialId = '{array7[1]}' and ISNULL(opernum,10) = '{array7[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'{, sqlConnection)}
```

### BOM_MaterialTreeMenu.cs#9 — line 1174
```sql
update materialdata set deletestatus = 1from materialdata inner join material on materialdata.materialid = material.materialid where materialcriteriaid = '{Conversions.ToString(CriteriaId)}' and material.materialid = '{Conversions.ToString(MaterialId)}' and materialdata.siteid = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and materialproductid = '{Conversions.ToString(SetMaterialProductId)}' and OperNum = '{Conversions.ToString(OperNum)}' and issubjob = '{Conversions.ToString(issubjob)}'
```

### BOM_MaterialTreeMenu.cs#10 — line 1268
```sql
update material set description = N'{description_textbox.Text.Trim().Replace(}'{,}''{)}' where materialid = '{text2}'
```

### BOM_MaterialTreeMenu.cs#11 — line 1271
```sql
update materialdata set formula = '{formula_textbox.Text.ToUpper().Replace(} {,}{).Replace(}'{,}''{)}', effectivedate = @effdate, obsdate = @obsdate, scrapfactor = '{scrapfactor_textbox.Text.ToUpper().Replace(} {,}{)}'
```

### BOM_MaterialTreeMenu.cs#12 — line 1304
```sql
update material set description = N'{description_textbox.Text.Trim().Replace(}'{,}''{)}' where materialid = '{array2[0]}'
```

### BOM_MaterialTreeMenu.cs#13 — line 1307
```sql
update materialsubjob set formula = '{formula_textbox.Text.ToUpper().Replace(} {,}{).Replace(} {,}{)
 .Replace(}'{,}''{)}', effectivedate = @effdate, obsdate = @obsdate, scrapfactor = '{scrapfactor_textbox.Text.ToUpper().Replace(} {,}{)}' where subjobmaterialid = '{array3[1]}' and materialid = '{array2[1]}' and ISNULL(opernum,10) = '{array2[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_MaterialTreeMenu.cs#14 — line 1328
```sql
update material set description = N'{description_textbox.Text.Trim().Replace(}'{,}''{)}' where materialid = '{array4[1]}'
```

### BOM_MaterialTreeMenu.cs#15 — line 1331
```sql
update materialsubjob set formula = '{formula_textbox.Text.ToUpper().Replace(} {,}{).Replace(} {,}{)
 .Replace(}'{,}''{)}', effectivedate = @effdate, obsdate = @obsdate, scrapfactor = '{scrapfactor_textbox.Text.ToUpper().Replace(} {,}{)}' where subjobmaterialid = '{array4[2]}' and materialid = '{array4[1]}' and ISNULL(opernum,10) = '{array4[0]}' and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_MaterialTreeMenu.cs#16 — line 1359
```sql
select description from material where material = '{material_textbox.Text}'
```

### BOM_MaterialTreeMenu.cs#17 — line 1428
```sql
exec Material_ItemPermutations '{HeaderLabel.Text}', '{SetProduct}%'
```

### BOM_MaterialTreeMenu.cs#18 — line 1437
```sql
exec Material_ItemPermutations_Special '{HeaderLabel.Text}', '{SetProduct}%'
```

### BOM_MaterialTreeMenu.cs#19 — line 1584
```sql
SELECT Item, Description FROM item WHERE item = '{MaterialString}'
```

### BOM_MaterialTreeMenu.cs#20 — line 1587
```sql
SELECT Item, Description FROM item_mst WHERE item = '{MaterialString}' AND site_ref = '{SetSite}'
```

### BOM_MaterialTreeMenu.cs#21 — line 1612
```sql
SELECT Item, Description FROM Item WHERE Item = '{MaterialString}'
```

### BOM_MaterialTreeMenu.cs#22 — line 1615
```sql
SELECT Item, Description FROM item_mst WHERE item = '{MaterialString}' AND site_ref = '{SetSite}'
```

### BOM_MaterialTreeMenu.cs#23 — line 1671
```sql
select MaterialId, Material from Material where Material = '{sendItem.Replace(} {,}{)}'{, sqlConnection)}
```

### BOM_MaterialTreeMenu.cs#24 — line 1676
```sql
insert into Material (Material, Description) values ('{sendItem.Replace(} {,}{)}', N'{sendDescription.Replace(}'{,}''{)}')
```

### BOM_MaterialTreeMenu.cs#25 — line 1678
```sql
select MaterialId, Material from Material where Material = '{sendItem.Replace(} {,}{)}'
```

### BOM_MaterialTreeMenu.cs#26 — line 1691
```sql
select 1 from MaterialSubjob where SubJobMaterialId = {ToSubJobMaterialId} and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}'
```

### BOM_MaterialTreeMenu.cs#27 — line 1698
```sql
Insert into MaterialSubjob (SubJobMaterialId, MaterialId, Formula, SiteId, Scrapfactor, EffectiveDate, ObsDate, IsSubJob,FamilyCode,RGID,OperNum) SELECT {ToSubJobMaterialId}, MaterialId, Formula, SiteId, Scrapfactor, EffectiveDate, ObsDate, IsSubJob,FamilyCode,RGID,OperNum FROM [MaterialSubJob] where subjobmaterialid= {FormSubJobMaterialId} and SiteId = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' and DeleteStatus = 0
```

## BOM_Replace.cs  (6)

### BOM_Replace.cs#1 — line 622
```sql
exec dbo.Material_FindGlobal_Replace '{listViewItem.SubItems[8].Text}', '{text}', '{listViewItem.SubItems[7].Text}', '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}', '{listViewItem.SubItems[6].Text}', '{listViewItem.SubItems[2].Text}'
```

### BOM_Replace.cs#2 — line 649
```sql
update materialdata set formula = '{listViewItem2.SubItems[4].Text.ToUpper()}' WHERE SITEID = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND materialproductid = '{Conversions.ToString(Conversions.ToInteger(listViewItem2.SubItems[6].Text))}' AND formula = '{listViewItem2.SubItems[3].Text}' AND DeleteStatus = 0
```

### BOM_Replace.cs#3 — line 690
```sql
update materialdata set ScrapFactor = '{listViewItem3.SubItems[4].Text.ToUpper()}' WHERE SITEID = '{Conversions.ToString(Global.SiteId(allowPLCOverride: false))}' AND materialproductid = '{Conversions.ToString(Conversions.ToInteger(listViewItem3.SubItems[6].Text))}' AND ScrapFactor = '{listViewItem3.SubItems[3].Text}' AND DeleteStatus = 0
```

### BOM_Replace.cs#4 — line 721
```sql
select MaterialId, Material from Material where Material = '{sendItem.Replace(} {,}{)}'{, sqlConnection)}
```

### BOM_Replace.cs#5 — line 726
```sql
insert into Material (Material, Description) values ('{sendItem.Replace(} {,}{)}', N'{sendDescription.Replace(}'{,}''{)}')
```

### BOM_Replace.cs#6 — line 728
```sql
select MaterialId, Material from Material where Material = '{sendItem.Replace(} {,}{)}'
```

## CatalogueItemsValidation.cs  (23)

### CatalogueItemsValidation.cs#1 — line 2123
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId WHERE puc.UserId = {Conversions.ToString(AuthenticateUser.UserId)} AND Catalogue.Status = 1 ORDER BY Catalogue.Name
```

### CatalogueItemsValidation.cs#2 — line 2140
```sql
SELECT SiteId, Description FROM Site WHERE SiteId NOT IN (20)
```

### CatalogueItemsValidation.cs#3 — line 2162
```sql
SELECT Currency_ID, Description, Symbol, Currency FROM Currency
```

### CatalogueItemsValidation.cs#4 — line 2589
```sql
SELECT DISTINCT cpc.ProductCategoryId, cpc.Name, CASE WHEN pc.Status <> 1 THEN pc.Status WHEN cpc.Status <> 1 THEN cpc.Status ELSE 1 END AS Status, CASE WHEN -1 = {Conversions.ToString(num)} THEN cpc.Name ELSE convert(VARCHAR, '10000000' + cpc.DisplayOrder) END AS DO FROM CatalogueProductCategories cpc INNER JOIN ProductCategory pc ON cpc.ProductCategoryId = pc.ProductCategoryId WHERE (cpc.CatalogueId = {Conversions.ToString(num)} Or -1 = {Conversions.ToString(num)}) ORDER BY DO
```

### CatalogueItemsValidation.cs#5 — line 2620
```sql
SELECT DISTINCT pc.ProductCodeId, pc.Product_Code, pc.Description FROM Product_Code pc INNER JOIN Product ON pc.ProductCodeId = Product.ProductCodeId AND Product.Status < 2 INNER JOIN Item ON Product.ProductId = Item.ProductId AND Item.Status < 2 INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = {Conversions.ToString(num)}
```

### CatalogueItemsValidation.cs#6 — line 2674
```sql
DELETE FROM PDMAudit.dbo.CatalogueItemValidationErrors WHERE DBName = '{Global.DBIdentity}' AND CatalogueId = {, _catalogueIdList[catalogue_selector.SelectedIndex]))}
```

### CatalogueItemsValidation.cs#7 — line 2725
```sql
INSERT INTO PDMAudit.dbo.CatalogueItemValidationErrors (DBName, CatalogueId, CategoryId, SiteId, CurrencyId, ItemId,
```

### CatalogueItemsValidation.cs#8 — line 2753
```sql
DELETE FROM PDMAudit.dbo.CatalogueProductValidationErrors WHERE DBName = '{Global.DBIdentity}' AND CatalogueId = {, _catalogueIdList[catalogue_selector.SelectedIndex]))}
```

### CatalogueItemsValidation.cs#9 — line 2870
```sql
INSERT INTO PDMAudit.dbo.CatalogueProductValidationErrors (DBName, CatalogueId, CategoryId, SiteId, CurrencyId, ProductId, ErrorDescription
```

### CatalogueItemsValidation.cs#10 — line 2879
```sql
DELETE FROM PDMAudit.dbo.TemplateValidationErrors WHERE DBName = '{Global.DBIdentity}' AND CatalogueId = {, _catalogueIdList[catalogue_selector.SelectedIndex]))}
```

### CatalogueItemsValidation.cs#11 — line 2892
```sql
INSERT INTO PDMAudit.dbo.TemplateValidationErrors (DBName, CatalogueId, CategoryId, SiteId, TemplateName, ErrorDescription)
```

### CatalogueItemsValidation.cs#12 — line 3561
```sql
SELECT pc.Name AS categoryname, pr.Name AS rangename FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId INNER JOIN ProductCategory pc ON pr.ProductCategoryId = pc.ProductCategoryId WHERE Item.ItemId = {Conversions.ToString(num)}
```

### CatalogueItemsValidation.cs#13 — line 3659
```sql
SELECT DISTINCT Item.Item, CASE WHEN pc.BasePriceRef = 1 THEN Item.BasePrice WHEN pc.BasePriceRef = 2 THEN Item.BasePrice2 WHEN pc.BasePriceRef = 3 THEN Item.BasePrice3 END AS base_price FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, _siteIdList[site_selector.SelectedIndex]),} {))}
```

### CatalogueItemsValidation.cs#14 — line 3704
```sql
SELECT DISTINCT Item.Item, CASE WHEN pc.BasePriceRef = 1 THEN Item.BasePrice WHEN pc.BasePriceRef = 2 THEN Item.BasePrice2 WHEN pc.BasePriceRef = 3 THEN Item.BasePrice3 END AS base_price FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, _siteIdList[site_selector.SelectedIndex]),} {))}
```

### CatalogueItemsValidation.cs#15 — line 3902
```sql
SELECT DISTINCT Item.Item, optval.OptionId, optval.OrderCodeValue, CASE WHEN pc.BasePriceRef = 1 THEN itov.IncrementalPrice WHEN pc.BasePriceRef = 2 THEN itov.IncrementalPrice2 WHEN pc.BasePriceRef = 3 THEN itov.IncrementalPrice3 END AS inc_price FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, _siteIdList[site_selector.SelectedIndex]),} {),}INNER JOIN ItemOptionValues itov ON Item.ItemId = itov.ItemId {),}INNER JOIN OptionValue optval ON itov.OptionValueId = optval.OptionValueId {))}
```

### CatalogueItemsValidation.cs#16 — line 4239
```sql
SELECT CatalogueId FROM Catalogue WHERE PrimarySiteId IN ({text4}) ORDER BY LeadTime, Name
```

### CatalogueItemsValidation.cs#17 — line 4250
```sql
SELECT DISTINCT optval.OrderCodeValue FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.IsFabric = 1 ORDER BY optval.OrderCodeValue
```

### CatalogueItemsValidation.cs#18 — line 4441
```sql
SELECT CatalogueId FROM Catalogue WHERE PrimarySiteId IN (1, 4) ORDER BY LeadTime, Name
```

### CatalogueItemsValidation.cs#19 — line 4600
```sql
SELECT SupplierCode FROM OptionValue WHERE OptionValueId = {Conversions.ToString(optvalId)}
```

### CatalogueItemsValidation.cs#20 — line 4674
```sql
SELECT DISTINCT Product.ProductId, Product.Product, pc.Product_Code, Product.Name AS prod_name, cat.Name AS cat_name FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId INNER JOIN ProductCategory cat ON pr.ProductCategoryId = cat.ProductCategoryId INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {Conversions.ToString(num2)}
```

### CatalogueItemsValidation.cs#21 — line 4711
```sql
SELECT DISTINCT OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = {Conversions.ToString(num5)}
```

### CatalogueItemsValidation.cs#22 — line 4738
```sql
SELECT DISTINCT attr.Name AS attr_name, atval.AttributeValueId, atval.Name AS atval_name, atval.OrderCodeValue, attr.DisplayOrder, atval.DisplayOrdinal, MIN(Catalogue.LeadTime) AS min_LT FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId INNER JOIN ProductAttributeValues pav ON atval.AttributeValueId = pav.AttributeValueId LEFT OUTER JOIN CatalogueAttributeValues cav ON atval.AttributeValueId = cav.AttributeValueId LEFT OUTER JOIN Catalogue ON cav.CatalogueId = Catalogue.CatalogueId AND Catalogue.Status = 1 GROUP BY attr.Name, atval.AttributeValueId, atval.Name, atval.OrderCodeValue, attr.DisplayOrder, atval.DisplayOrdinal, pav.ProductId HAVING pav.ProductId = {, arrayList2[k]),} AND atval.OrderCodeValue IS NOT NULL {),}ORDER BY attr.DisplayOrder, atval.DisplayOrdinal{))}
```

### CatalogueItemsValidation.cs#23 — line 4772
```sql
SELECT DISTINCT Item.ItemId, Item.Item, dbo.fnGetListPriceByItem(Item.Item, '{text3}', GetUTCDate(), {Conversions.ToString(num2)}, NULL) AS list_Price, MIN(Catalogue.LeadTime) AS min_LT, Item.WeightKilos, Item.VolumeLitres, Product.IsSuperProduct FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId INNER JOIN Catalogue ON ci.CatalogueId = Catalogue.CatalogueId GROUP BY Item.ItemId, Item.Item, Item.ProductId, Item.WeightKilos, Item.VolumeLitres, Product.IsSuperProduct HAVING Item.ProductId = {, arrayList2[k]),} AND Item.Item LIKE '{), text2),}%' {))}
```

## DPS.cs  (37)

### DPS.cs#1 — line 1396
```sql
SELECT SiteId, Description FROM Site
```

### DPS.cs#2 — line 1416
```sql
SELECT Language_ID, Language FROM Language
```

### DPS.cs#3 — line 1436
```sql
SELECT Currency_ID, Description FROM Currency
```

### DPS.cs#4 — line 1486
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId WHERE puc.UserId = {Conversions.ToString(AuthenticateUser.UserId)} AND Catalogue.Status = 1 AND Catalogue.LoanStock = 0
```

### DPS.cs#5 — line 1499
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, {Conversions.ToString(num)} AS ReadOnly FROM Catalogue WHERE Catalogue.Status = 1 AND Catalogue.LoanStock = 0
```

### DPS.cs#6 — line 1651
```sql
SELECT CountryName, ISOCode FROM CPCSourceCountries cpcsc INNER JOIN Country ON cpcsc.SourceCountryId = Country.CountryId WHERE CatalogueId = {Conversions.ToString(num2)} AND ProductCategoryId = {, thisdata.CategoryId[i]))}
```

### DPS.cs#7 — line 1678
```sql
SELECT CountryName, ISOCode FROM CPCSourceCountries cpcsc INNER JOIN Country ON cpcsc.SourceCountryId = Country.CountryId WHERE CatalogueId = {Conversions.ToString(num4)} AND ProductCategoryId = {, thisdata.CategoryId[i]))}
```

### DPS.cs#8 — line 1745
```sql
SELECT Currency FROM Currency WHERE Currency_ID = {Conversions.ToString(Global.currencyId)}
```

### DPS.cs#9 — line 1905
```sql
SELECT dc.CatalogueId FROM DealerCatalogues dc INNER JOIN Catalogue ON dc.CatalogueId = Catalogue.CatalogueId WHERE dc.DealerNumId = {Conversions.ToString(dealerNum)} AND Catalogue.LoanStock = 0
```

### DPS.cs#10 — line 1909
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId WHERE puc.UserId = {Conversions.ToString(AuthenticateUser.UserId)} AND Catalogue.Status = 1 AND Catalogue.LoanStock = 0
```

### DPS.cs#11 — line 1985
```sql
SELECT dc.CatalogueId FROM DealerCatalogues dc INNER JOIN Catalogue ON dc.CatalogueId = Catalogue.CatalogueId WHERE dc.DealerNumId = {Conversions.ToString(dealerNum)} AND Catalogue.LoanStock = 0
```

### DPS.cs#12 — line 1989
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId WHERE puc.UserId = {Conversions.ToString(AuthenticateUser.UserId)} AND Catalogue.Status = 1 AND Catalogue.LoanStock = 0
```

### DPS.cs#13 — line 2065
```sql
SELECT dc.CatalogueId FROM DealerCatalogues dc INNER JOIN Catalogue ON dc.CatalogueId = Catalogue.CatalogueId WHERE dc.DealerNumId = {Conversions.ToString(dealerNum)} AND Catalogue.LoanStock = 0
```

### DPS.cs#14 — line 2069
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId WHERE puc.UserId = {Conversions.ToString(AuthenticateUser.UserId)} AND Catalogue.Status = 1 AND Catalogue.LoanStock = 0
```

### DPS.cs#15 — line 2152
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId FROM DealerCatalogues dc INNER JOIN Catalogue ON dc.CatalogueId = Catalogue.CatalogueId INNER JOIN DealerNums dn ON dc.DealerNumId = dn.DealerNumId WHERE dn.DealerNum = '{dealerNum}' AND Catalogue.Status = 1 ORDER BY Catalogue.Name
```

### DPS.cs#16 — line 2160
```sql
SELECT SiteId FROM Site WHERE Site = '{site}'
```

### DPS.cs#17 — line 2168
```sql
SELECT top 1 Currency_ID FROM Currency WHERE Currency = '{currency}'
```

### DPS.cs#18 — line 2176
```sql
SELECT Language_ID FROM Language WHERE CultureCode = '{language}'
```

### DPS.cs#19 — line 2266
```sql
SELECT CatalogueId FROM DealerCatalogues WHERE DealerNumId = {Conversions.ToString(dealerNum)}
```

### DPS.cs#20 — line 2287
```sql
SELECT USCatalogue FROM Catalogue WHERE CatalogueId = {Conversions.ToString(catalogueId)}
```

### DPS.cs#21 — line 2303
```sql
SELECT OrderType FROM Catalogue WHERE CatalogueId = {, quoteData.CatalogueId[i]))}
```

### DPS.cs#22 — line 2373
```sql
SELECT CatalogueId FROM DealerCatalogues WHERE DealerNumId = {Conversions.ToString(dealerNum)}
```

### DPS.cs#23 — line 2395
```sql
SELECT USCatalogue FROM Catalogue WHERE CatalogueId = {Conversions.ToString(catalogueId)}
```

### DPS.cs#24 — line 2416
```sql
SELECT OrderType FROM Catalogue WHERE CatalogueId = {Conversions.ToString(num3)}
```

### DPS.cs#25 — line 2475
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DPS.cs#26 — line 2478
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DPS.cs#27 — line 2487
```sql
INSERT INTO PDMAudit.dbo.{auditTable} (TransactionId, {fieldName1}, {fieldName2}, {fieldName3}
```

### DPS.cs#28 — line 2615
```sql
SELECT DISTINCT TOP {Conversions.ToString(num)} md.DeleteStatus, matl.MaterialId, matl.Material FROM Material matl LEFT OUTER JOIN MaterialData md ON matl.MaterialId = md.MaterialId WHERE matl.Material Like '=IF%'
```

### DPS.cs#29 — line 2688
```sql
SELECT SubJobMaterialId FROM MaterialSubJob WHERE MaterialId = {arrayList[i].ToString()}
```

### DPS.cs#30 — line 2701
```sql
DELETE FROM MaterialData WHERE MaterialId = {arrayList[i].ToString()}
```

### DPS.cs#31 — line 2704
```sql
DELETE FROM Material WHERE MaterialId = {arrayList[i].ToString()}
```

### DPS.cs#32 — line 3197
```sql
SELECT DISTINCT PSTemplateFile FROM CatalogueProductCategories ORDER BY PSTemplateFile
```

### DPS.cs#33 — line 3232
```sql
SELECT attr.AttributeId FROM CatalogueProductCategories cpc INNER JOIN Attribute attr ON cpc.ProductCategoryId = attr.ProductCategoryId WHERE cpc.PSTemplateFile = '{text2}'
```

### DPS.cs#34 — line 3240
```sql
SELECT opt.OptionId FROM CatalogueProductCategories cpc INNER JOIN [Option] opt ON cpc.ProductCategoryId = opt.ProductCategoryId WHERE cpc.PSTemplateFile = '{text2}'
```

### DPS.cs#35 — line 3267
```sql
SELECT AttributeId FROM Attribute WHERE AttributeId = {Conversions.ToString(num2)}
```

### DPS.cs#36 — line 3287
```sql
SELECT OptionId FROM [Option] WHERE OptionId = {Conversions.ToString(num3)}
```

### DPS.cs#37 — line 3353
```sql
SELECT DISTINCT PSTemplateFile FROM PDMTest.dbo.CatalogueProductCategories ORDER BY PSTemplateFile
```

## DataList.cs  (122)

### DataList.cs#1 — line 259
```sql
SELECT DISTINCT pr.ProductRangeId FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### DataList.cs#2 — line 292
```sql
SELECT DISTINCT atval.AttributeValueId FROM ProductAttributeValues pav INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE attr.ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### DataList.cs#3 — line 334
```sql
SELECT DISTINCT optval.OptionValueId FROM ProductOptionValues pov INNER JOIN OptionValue optval ON pov.OptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### DataList.cs#4 — line 352
```sql
SELECT DISTINCT optval.OptionValueId FROM ProductRangeOptionValues prov INNER JOIN OptionValue optval ON prov.OptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### DataList.cs#5 — line 370
```sql
SELECT DISTINCT dav.AdditionalOptionValueId FROM DependentAttributeValues dav INNER JOIN OptionValue optval ON dav.AdditionalOptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### DataList.cs#6 — line 390
```sql
SELECT DISTINCT dov.AdditionalOptionValueId FROM DependentOptionValues dov INNER JOIN OptionValue optval ON dov.AdditionalOptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### DataList.cs#7 — line 562
```sql
Delete Redundant Value{:
 text = ((Operators.CompareString(tableType,}ProductRange{, TextCompare: false) != 0) ? (}UPDATE {tableType}Value SET Status = -1 WHERE {tableType}ValueId = {Conversions.ToString(menuId)) : (}UPDATE ProductRange SET Status = -1 WHERE ProductRangeId = {Conversions.ToString(menuId)))}
```

### DataList.cs#8 — line 566
```sql
DELETE FROM Catalogue{tableType}Values WHERE {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#9 — line 572
```sql
Delete All Redundant Values{:
 {
 int num6 = -1}
```

### DataList.cs#10 — line 575
```sql
SELECT {tableType}Id FROM {tableType}Value WHERE {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#11 — line 584
```sql
SELECT {tableType}ValueId FROM {tableType}Value WHERE {tableType}Id = {Conversions.ToString(num6)}
```

### DataList.cs#12 — line 602
```sql
UPDATE {tableType}Value SET Status = -1 WHERE {tableType}ValueId = {, arrayList3[k]))}
```

### DataList.cs#13 — line 605
```sql
DELETE FROM Catalogue{tableType}Values WHERE {tableType}ValueId = {, arrayList3[k]))}
```

### DataList.cs#14 — line 615
```sql
INSERT INTO CatalogueProductRanges (CatalogueId, ProductRangeId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)})
```

### DataList.cs#15 — line 620
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#16 — line 623
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#17 — line 632
```sql
INSERT INTO PDMAudit.dbo.CPRUpdates (TransactionId, CatalogueId, ProductRangeId, ActionTaken) VALUES ({Conversions.ToString(num5)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)}, 'ADDED')
```

### DataList.cs#18 — line 648
```sql
INSERT INTO Catalogue{tableType}Values (CatalogueId, {tableType}ValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)})
```

### DataList.cs#19 — line 653
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#20 — line 656
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#21 — line 665
```sql
INSERT INTO PDMAudit.dbo.C{tableType.Substring(0, 1)}VUpdates (TransactionId, CatalogueId, {tableType}ValueId, ActionTaken) VALUES ({Conversions.ToString(num3)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)}, 'ADDED')
```

### DataList.cs#22 — line 675
```sql
SELECT COUNT(*) AS cnt FROM Product{tableType}Values WHERE ProductId = {Conversions.ToString(Global.productId)} AND {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#23 — line 695
```sql
SELECT {tableType}Id FROM {tableType}Value WHERE {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#24 — line 708
```sql
SELECT DISTINCT {tableType}Value.{tableType}ValueId FROM {tableType}Value LEFT OUTER JOIN Catalogue{tableType}Values cv ON {tableType}Value.{tableType}ValueId = cv.{tableType}ValueId AND cv.CatalogueId = {Conversions.ToString(Global.catalogueId)} WHERE {tableType}Value.{tableType}Id = {Conversions.ToString(num8)} AND cv.{tableType}ValueId IS NULL
```

### DataList.cs#25 — line 724
```sql
INSERT INTO Catalogue{tableType}Values (CatalogueId, {tableType}ValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(num10)})
```

### DataList.cs#26 — line 729
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#27 — line 732
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#28 — line 741
```sql
INSERT INTO PDMAudit.dbo.C{tableType.Substring(0, 1)}VUpdates (TransactionId, CatalogueId, {tableType}ValueId, ActionTaken) VALUES ({Conversions.ToString(num11)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(num10)}, 'ADDED')
```

### DataList.cs#29 — line 755
```sql
INSERT INTO Catalogue{tableType}Values (CatalogueId, {tableType}ValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)})
```

### DataList.cs#30 — line 760
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#31 — line 763
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#32 — line 772
```sql
INSERT INTO PDMAudit.dbo.C{tableType.Substring(0, 1)}VUpdates (TransactionId, CatalogueId, {tableType}ValueId, ActionTaken) VALUES ({Conversions.ToString(num30)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)}, 'ADDED')
```

### DataList.cs#33 — line 794
```sql
SELECT DISTINCT Product.Product, pav.AttributeValueId AS pav_atvalId, mpv.AttributeValueId AS mpv_atvalId FROM Product INNER JOIN ProductAttributeValues pav On Product.ProductId = pav.ProductId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER Join Attribute attr ON atval.AttributeId = attr.AttributeId And attr.AttributeType = 0 LEFT OUTER JOIN MaterialProductIdValues mpv ON pav.AttributeValueId = mpv.AttributeValueId WHERE Product.ProductId = {Conversions.ToString(Global.productId)}
```

### DataList.cs#34 — line 820
```sql
SELECT COUNT(*) AS cnt FROM Catalogue{tableType}Values WHERE {tableType}ValueId = {Conversions.ToString(menuId)} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### DataList.cs#35 — line 830
```sql
INSERT INTO Catalogue{tableType}Values (CatalogueId, {tableType}ValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)})
```

### DataList.cs#36 — line 839
```sql
SELECT COUNT(*) AS cnt FROM Product{tableType}Values WHERE {tableType}ValueId = {Conversions.ToString(menuId)} AND ProductId = {Conversions.ToString(Global.productId)}
```

### DataList.cs#37 — line 849
```sql
INSERT INTO Product{tableType}Values (ProductId, {tableType}ValueId) VALUES ({Conversions.ToString(Global.productId)}, {Conversions.ToString(menuId)})
```

### DataList.cs#38 — line 854
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#39 — line 857
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#40 — line 866
```sql
INSERT INTO PDMAudit.dbo.P{tableType.Substring(0, 1)}VUpdates (TransactionId, ProductId, {tableType}ValueId, ActionTaken) VALUES ({Conversions.ToString(num27)}, {Conversions.ToString(Global.productId)}, {Conversions.ToString(menuId)}, 'ADDED')
```

### DataList.cs#41 — line 939
```sql
SELECT Product FROM Product WHERE ProductId IN (-1
```

### DataList.cs#42 — line 986
```sql
SELECT COUNT(*) AS cnt FROM Catalogue{tableType}Values WHERE {tableType}ValueId = {Conversions.ToString(menuId)} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### DataList.cs#43 — line 996
```sql
INSERT INTO Catalogue{tableType}Values (CatalogueId, {tableType}ValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)})
```

### DataList.cs#44 — line 1008
```sql
SELECT COUNT(*) AS cnt FROM Product{tableType}Values WHERE {tableType}ValueId = {Conversions.ToString(menuId)} AND ProductId = {, arrayList6[num18]))}
```

### DataList.cs#45 — line 1020
```sql
INSERT INTO Product{tableType}Values (ProductId, {tableType}ValueId) VALUES ({, arrayList6[num18]),}, {), menuId),}){))}
```

### DataList.cs#46 — line 1025
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#47 — line 1028
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#48 — line 1037
```sql
INSERT INTO PDMAudit.dbo.P{tableType.Substring(0, 1)}VUpdates (TransactionId, ProductId, {tableType}ValueId, ActionTaken) VALUES ({Conversions.ToString(num19)}, {, arrayList6[num18]),}, {), menuId),}, 'ADDED'){))}
```

### DataList.cs#49 — line 1100
```sql
SELECT ProductId FROM Product{tableType}Values WHERE ProductId = {Conversions.ToString(num42)} AND {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#50 — line 1112
```sql
SELECT ProductId FROM Product WHERE ProductId = {Conversions.ToString(num42)} AND ProductRangeId = {Conversions.ToString(num39)}
```

### DataList.cs#51 — line 1126
```sql
SELECT COUNT(*) AS cnt FROM Catalogue{tableType}Values WHERE {tableType}ValueId = {Conversions.ToString(menuId)} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### DataList.cs#52 — line 1136
```sql
INSERT INTO Catalogue{tableType}Values (CatalogueId, {tableType}ValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)})
```

### DataList.cs#53 — line 1144
```sql
INSERT INTO Product{tableType}Values (ProductId, {tableType}ValueId) VALUES ({Conversions.ToString(num42)}, {Conversions.ToString(menuId)})
```

### DataList.cs#54 — line 1149
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#55 — line 1152
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#56 — line 1161
```sql
INSERT INTO PDMAudit.dbo.P{tableType.Substring(0, 1)}VUpdates (TransactionId, ProductId, {tableType}ValueId, ActionTaken) VALUES ({Conversions.ToString(num44)}, {Conversions.ToString(num42)}, {Conversions.ToString(menuId)}, 'ADDED')
```

### DataList.cs#57 — line 1183
```sql
DELETE FROM CatalogueProductRanges WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductRangeId = {Conversions.ToString(menuId)}
```

### DataList.cs#58 — line 1188
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#59 — line 1191
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#60 — line 1200
```sql
INSERT INTO PDMAudit.dbo.CPRUpdates (TransactionId, CatalogueId, ProductRangeId, ActionTaken) VALUES ({Conversions.ToString(num28)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)}, 'REMOVED')
```

### DataList.cs#61 — line 1210
```sql
DELETE FROM Catalogue{tableType}Values WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#62 — line 1215
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#63 — line 1218
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#64 — line 1227
```sql
INSERT INTO PDMAudit.dbo.C{tableType.Substring(0, 1)}VUpdates (TransactionId, CatalogueId, {tableType}ValueId, ActionTaken) VALUES ({Conversions.ToString(num29)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(menuId)}, 'REMOVED')
```

### DataList.cs#65 — line 1238
```sql
DELETE FROM CatalogueProductOptionExclusions WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND {tableType}ValueId = {Conversions.ToString(menuId)} AND ProductId = {Conversions.ToString(Global.productId)}
```

### DataList.cs#66 — line 1249
```sql
INSERT INTO CatalogueProductOptionExclusions (CatalogueId, ProductId, OptionValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(Global.productId)}, {Conversions.ToString(menuId)})
```

### DataList.cs#67 — line 1268
```sql
SELECT DISTINCT Product.Product, pav.AttributeValueId AS pav_atvalId, mpv.AttributeValueId AS mpv_atvalId FROM Product INNER JOIN ProductAttributeValues pav On Product.ProductId = pav.ProductId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER Join Attribute attr ON atval.AttributeId = attr.AttributeId And attr.AttributeType = 0 LEFT OUTER JOIN MaterialProductIdValues mpv ON pav.AttributeValueId = mpv.AttributeValueId WHERE Product.ProductId = {Conversions.ToString(Global.productId)}
```

### DataList.cs#68 — line 1293
```sql
SELECT DISTINCT Catalogue.Name FROM Catalogue INNER JOIN CatalogueItems ci ON Catalogue.CatalogueId = ci.CatalogueId INNER JOIN Item ON ci.ItemId = Item.ItemId WHERE Item.ProductId = {Conversions.ToString(Global.productId)} ORDER BY Catalogue.Name
```

### DataList.cs#69 — line 1305
```sql
SELECT Name, OrderCodeValue FROM {tableType}Value WHERE {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#70 — line 1328
```sql
DELETE FROM Product{tableType}Values WHERE ProductId = {Conversions.ToString(Global.productId)} AND {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#71 — line 1333
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#72 — line 1336
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#73 — line 1345
```sql
INSERT INTO PDMAudit.dbo.P{tableType.Substring(0, 1)}VUpdates (TransactionId, ProductId, {tableType}ValueId, ActionTaken) VALUES ({Conversions.ToString(num23)}, {Conversions.ToString(Global.productId)}, {Conversions.ToString(menuId)}, 'REMOVED')
```

### DataList.cs#74 — line 1408
```sql
DELETE FROM Product{tableType}Values WHERE ProductId = {Conversions.ToString(num37)} AND {tableType}ValueId = {Conversions.ToString(menuId)} AND ProductId IN (SELECT ProductId FROM Product WHERE ProductRangeId = {Conversions.ToString(num34)})
```

### DataList.cs#75 — line 1416
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#76 — line 1419
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#77 — line 1428
```sql
INSERT INTO PDMAudit.dbo.P{tableType.Substring(0, 1)}VUpdates (TransactionId, ProductId, {tableType}ValueId, ActionTaken) VALUES ({Conversions.ToString(num38)}, {Conversions.ToString(num37)}, {Conversions.ToString(menuId)}, 'REMOVED')
```

### DataList.cs#78 — line 1453
```sql
SELECT Name, OrderCodeFormatString FROM ProductRange WHERE ProductRangeId = {menuId}
```

### DataList.cs#79 — line 1465
```sql
UPDATE ProductRange SET OrderCodeFormatString = NULL WHERE ProductRangeId = {menuId}
```

### DataList.cs#80 — line 1469
```sql
UPDATE ProductRange SET OrderCodeFormatString = '{text13.Replace(}({,}{{).Replace(}){,}}{)}' WHERE ProductRangeId = {menuId}
```

### DataList.cs#81 — line 1492
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#82 — line 1495
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#83 — line 1504
```sql
INSERT INTO PDMAudit.dbo.ProductRangeOCFS (TransactionId, ProductRangeId, PrevOCFS, NewOCFS) VALUES ({Conversions.ToString(num33)}, {menuId}, '{text11}', '{text13}')
```

### DataList.cs#84 — line 1516
```sql
SELECT ImageFile FROM {tableType}Value WHERE {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#85 — line 1538
```sql
UPDATE {tableType}Value SET ImageFile = '{text7}' WHERE {tableType}ValueId = {Conversions.ToString(menuId)}
```

### DataList.cs#86 — line 1628
```sql
Delete Redundant Value{)}
```

### DataList.cs#87 — line 1630
```sql
Delete All Redundant Values{)}
```

### DataList.cs#88 — line 1647
```sql
SELECT IsFabric FROM [Option] opt INNER JOIN OptionValue optval ON opt.OptionId = optval.OptionId WHERE OptionValueId = {menuId}
```

### DataList.cs#89 — line 1818
```sql
Delete Redundant Value{)}
```

### DataList.cs#90 — line 1819
```sql
Delete All Redundant Values{)}
```

### DataList.cs#91 — line 1918
```sql
SELECT AttributeType FROM Attribute WHERE AttributeId = {Conversions.ToString(parentId)}
```

### DataList.cs#92 — line 1966
```sql
SELECT IsFabric FROM [Option] WHERE OptionId = {Conversions.ToString(parentId)}
```

### DataList.cs#93 — line 1986
```sql
SELECT DISTINCT {tableType}Id FROM Catalogue{tableType}s WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### DataList.cs#94 — line 1997
```sql
SELECT DISTINCT {tableType}ValueId FROM Catalogue{tableType}Values WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### DataList.cs#95 — line 2009
```sql
SELECT DISTINCT {tableType}ValueId FROM CatalogueProductOptionExclusions WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductId = {Conversions.ToString(Global.productId)}
```

### DataList.cs#96 — line 2221
```sql
SELECT DISTINCT OrderCodeValue FROM {tableType}Value WHERE OrderCodeValue = '{DataGrid1[i, 3].ToString()}' AND Status >= 0 AND {tableType}Id = {Conversions.ToString(parentId)}
```

### DataList.cs#97 — line 2233
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription
```

### DataList.cs#98 — line 2245
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num2)}, {Conversions.ToString(Global.languageId)}, '{text2}', '
```

### DataList.cs#99 — line 2251
```sql
SELECT TOP 1 ProductRangeId FROM ProductRange WHERE ProductRangeId <> 999 AND ProductRangeId <> 1000
```

### DataList.cs#100 — line 2256
```sql
SELECT TOP 1 {tableType}ValueId FROM {tableType}Value
```

### DataList.cs#101 — line 2274
```sql
SELECT TOP 1 DisplayOrdinal FROM {tableType}Value WHERE {tableType}Id = {Conversions.ToString(parentId)} ORDER BY DisplayOrdinal DESC{) : (}SELECT TOP 1 DisplayOrder FROM ProductRange WHERE ProductCategoryId = {Conversions.ToString(parentId)} ORDER BY DisplayOrder DESC{))}
```

### DataList.cs#102 — line 2285
```sql
SELECT OrderCodeFormatString FROM ProductRange WHERE ProductCategoryId = {Conversions.ToString(parentId)}
```

### DataList.cs#103 — line 2297
```sql
INSERT INTO ProductRange (ProductCategoryId, Name, OrderCodeFormatString, DisplayOrder, DescriptionId, Status) VALUES ({Conversions.ToString(parentId)}, '{text2}',
```

### DataList.cs#104 — line 2303
```sql
INSERT INTO {tableType}Value ({tableType}Id, Name,
```

### DataList.cs#105 — line 2329
```sql
SELECT TOP 1 ProductRangeId FROM ProductRange WHERE ProductRangeId <> 999 AND ProductRangeId <> 1000 AND ProductCategoryId = {Conversions.ToString(parentId)} ORDER BY ProductRangeId DESC
```

### DataList.cs#106 — line 2338
```sql
INSERT INTO CatalogueProductRanges (CatalogueId, ProductRangeId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(num5)})
```

### DataList.cs#107 — line 2377
```sql
SELECT DISTINCT OrderCodeValue FROM {tableType}Value WHERE OrderCodeValue = '{DataGrid1[i, 3].ToString()}' AND Status >= 0 AND {tableType}Id = {Conversions.ToString(parentId)} AND {tableType}ValueId <> {text4}
```

### DataList.cs#108 — line 2403
```sql
SELECT Status, Name FROM {tableType}Value WHERE {tableType}ValueId = {DataGrid1[i, 0].ToString()) : (}SELECT Status, Name FROM ProductRange WHERE ProductRangeId = {DataGrid1[i, 0].ToString()))}
```

### DataList.cs#109 — line 2414
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#110 — line 2417
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#111 — line 2428
```sql
INSERT INTO PDMAudit.dbo.ASUpdates (TransactionId, AttributeValueId, Status, PrevStatus, ActionTaken, Description) VALUES ({Conversions.ToString(num7)}, {DataGrid1[i, 0].ToString()}, {Conversions.ToString(num6)}, {Conversions.ToString(num6)}, '[RENAMED]', '{Strings.Trim(DataGrid1[i, 2].ToString())}')
```

### DataList.cs#112 — line 2434
```sql
INSERT INTO PDMAudit.dbo.OSUpdates (TransactionId, OptionValueId, Status, PrevStatus, ActionTaken, Description) VALUES ({Conversions.ToString(num7)}, {DataGrid1[i, 0].ToString()}, {Conversions.ToString(num6)}, {Conversions.ToString(num6)}, '[RENAMED]', '{Strings.Trim(DataGrid1[i, 2].ToString())}')
```

### DataList.cs#113 — line 2443
```sql
UPDATE ProductRange SET Name = '{Strings.Trim(DataGrid1[i, 2].ToString())}',
```

### DataList.cs#114 — line 2458
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#115 — line 2461
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#116 — line 2470
```sql
INSERT INTO PDMAudit.dbo.ProductRangeOCFS (TransactionId, ProductRangeId, PrevOCFS, NewOCFS) VALUES ({Conversions.ToString(num8)}, {DataGrid1[i, 0].ToString()}, '{text5}', '{text6}')
```

### DataList.cs#117 — line 2477
```sql
UPDATE {tableType}Value SET Name = '{Strings.Trim(DataGrid1[i, 2].ToString())}',
```

### DataList.cs#118 — line 2484
```sql
UPDATE AttributeValue SET ModelSuffix = '{DataGrid1[i, 3].ToString()}' WHERE AttributeValueId = {DataGrid1[i, 0].ToString()}
```

### DataList.cs#119 — line 2502
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DataList.cs#120 — line 2505
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DataList.cs#121 — line 2514
```sql
INSERT INTO PDMAudit.dbo.{tableType.Substring(0, 1)}SUpdates (TransactionId, {tableType}ValueId, Status, PrevStatus, ActionTaken, Description) VALUES ({Conversions.ToString(num9)}, {DataGrid1[i, 0].ToString()}, {parseStatus(DataGrid1[i, 5].ToString())}, {Conversions.ToString(num6)}, '{DataGrid1[i, 5].ToString()}', '{Strings.Trim(DataGrid1[i, 2].ToString())}')
```

### DataList.cs#122 — line 2521
```sql
SELECT ShortDescription, RelatedTable FROM OtherDescription WHERE DescriptionId = {DataGrid1[i, 1].ToString()} AND LanguageId = 1
```

## DeleteThread.cs  (8)

### DeleteThread.cs#1 — line 47
```sql
SELECT COUNT(*) AS cnt FROM ProductOptionValues WHERE OptionValueId IN (SELECT OptionValueId FROM OptionValue WHERE OptionId IN ({Conversions.ToString(num3)}, -1) UNION SELECT -1)
```

### DeleteThread.cs#2 — line 68
```sql
DELETE FROM CatalogueOptionValues WHERE OptionValueId IN (SELECT OptionValueId FROM OptionValue WHERE OptionId IN ({Conversions.ToString(num3)}, -1) UNION SELECT -1)
```

### DeleteThread.cs#3 — line 77
```sql
DELETE FROM DependentOptionValues WHERE OptionValueId IN (SELECT OptionValueId FROM OptionValue WHERE OptionId IN ({Conversions.ToString(num3)}, -1) UNION SELECT -1)
```

### DeleteThread.cs#4 — line 86
```sql
DELETE FROM OptionValue WHERE OptionId IN ({Conversions.ToString(num3)}, -1)
```

### DeleteThread.cs#5 — line 95
```sql
DELETE FROM HandbookOptions WHERE OptionId IN ({Conversions.ToString(num3)}, -1)
```

### DeleteThread.cs#6 — line 104
```sql
DELETE FROM [Option] WHERE OptionId IN ({Conversions.ToString(num3)}, -1)
```

### DeleteThread.cs#7 — line 119
```sql
SELECT OptionId FROM [Option] WITH (NOLOCK) WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} ORDER BY DisplayOrder
```

### DeleteThread.cs#8 — line 134
```sql
UPDATE [Option] SET DisplayOrder = {Conversions.ToString(k + 1)} WHERE OptionId = {, arrayList[k]))}
```

## DependencyManager.cs  (38)

### DependencyManager.cs#1 — line 574
```sql
SELECT cpoe.OptionValueId, opt.Name + ' - ' + optval.Name + ' (' + optval.OrderCodeValue + ')' AS NamePair FROM CatalogueProductOptionExclusions cpoe INNER JOIN OptionValue optval ON cpoe.OptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE cpoe.CatalogueId = {Conversions.ToString(Global.catalogueId)} AND cpoe.ProductId = {_productIds[parent_atvals.SelectedIndex].ToString()} ORDER BY opt.DisplayOrder, optval.DisplayOrdinal{) : ((!attributeValueExclusionMode) ? (}SELECT dav.AdditionalOptionValueId, opt.Name + ' - ' + optval.Name + ' (' + optval.OrderCodeValue + ')' AS NamePair FROM DependentAttributeValues dav INNER JOIN OptionValue optval ON dav.AdditionalOptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE Status = 1 AND dav.AttributeValueId = {_parentAtValIds[parent_atvals.SelectedIndex].ToString()} AND (opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)} OR opt.IsFabric = 1) ORDER BY opt.DisplayOrder, optval.DisplayOrdinal{) : (}SELECT ave.ExcludedAttributeValueId, attr.Name + ' - ' + atval.Name + ' (' + atval.OrderCodeValue + ')' AS NamePair FROM AttributeValueExclusions ave INNER JOIN AttributeValue atval ON ave.ExcludedAttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND ave.AttributeValueId = {_parentAtValIds[parent_atvals.SelectedIndex].ToString()} AND (attr.ProductCategoryId = {Conversions.ToString(Global.categoryId)}) ORDER BY attr.DisplayOrder, atval.DisplayOrdinal{)))}
```

### DependencyManager.cs#2 — line 663
```sql
SELECT dov.AdditionalOptionValueId, opt.Name + ' - ' + optval.Name + ' (' + optval.OrderCodeValue + ')' AS NamePair FROM DependentOptionValues dov INNER JOIN OptionValue optval ON dov.AdditionalOptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE Status = 1 AND dov.OptionValueId = {_parentOptValIds[parent_optvals.SelectedIndex].ToString()} AND (opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)} OR opt.IsFabric = 1) ORDER BY opt.DisplayOrder, optval.DisplayOrdinal
```

### DependencyManager.cs#3 — line 750
```sql
SELECT OptionValueId FROM CatalogueProductOptionExclusions WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductId = {_productIds[parent_atvals.SelectedIndices[j]].ToString()} AND OptionValueId = {Conversions.ToString(num2)}
```

### DependencyManager.cs#4 — line 760
```sql
INSERT INTO CatalogueProductOptionExclusions (CatalogueId, ProductId, OptionValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {_productIds[parent_atvals.SelectedIndices[j]].ToString()}, {Conversions.ToString(num2)})
```

### DependencyManager.cs#5 — line 776
```sql
SELECT ExcludedAttributeValueId FROM AttributeValueExclusions WHERE AttributeValueId = {_parentAtValIds[parent_atvals.SelectedIndex].ToString()} AND ExcludedAttributeValueId = {Conversions.ToString(num2)}
```

### DependencyManager.cs#6 — line 786
```sql
INSERT INTO AttributeValueExclusions (AttributeValueId, ExcludedAttributeValueId) VALUES ({_parentAtValIds[parent_atvals.SelectedIndex].ToString()}, {Conversions.ToString(num2)})
```

### DependencyManager.cs#7 — line 797
```sql
INSERT INTO DependentAttributeValues (AttributeValueId, AdditionalOptionValueId) VALUES ({_parentAtValIds[parent_atvals.SelectedIndex].ToString()}, {Conversions.ToString(num2)})
```

### DependencyManager.cs#8 — line 802
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DependencyManager.cs#9 — line 805
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DependencyManager.cs#10 — line 814
```sql
INSERT INTO PDMAudit.dbo.DAVUpdates (TransactionId, AttributeValueId, AdditionalOptionValueId, ActionTaken) VALUES ({Conversions.ToString(num5)}, {_parentAtValIds[parent_atvals.SelectedIndex].ToString()}, {Conversions.ToString(num2)}, 'ADDED')
```

### DependencyManager.cs#11 — line 833
```sql
INSERT INTO DependentOptionValues (OptionValueId, AdditionalOptionValueId) VALUES ({_parentOptValIds[parent_optvals.SelectedIndex].ToString()}, {Conversions.ToString(num2)})
```

### DependencyManager.cs#12 — line 838
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DependencyManager.cs#13 — line 841
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DependencyManager.cs#14 — line 850
```sql
INSERT INTO PDMAudit.dbo.DOVUpdates (TransactionId, OptionValueId, AdditionalOptionValueId, ActionTaken) VALUES ({Conversions.ToString(num6)}, {_parentOptValIds[parent_optvals.SelectedIndex].ToString()}, {Conversions.ToString(num2)}, 'ADDED')
```

### DependencyManager.cs#15 — line 917
```sql
SELECT DISTINCT OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### DependencyManager.cs#16 — line 944
```sql
SELECT DISTINCT OptionValueId FROM OptionValue WHERE OptionId IN (SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN CatalogueOptionValues cov ON optval.OptionValueId = cov.OptionValueId INNER JOIN Catalogue ON cov.CatalogueId = Catalogue.CatalogueId AND Catalogue.Name LIKE '%POSH%' UNION SELECT -1) AND OptionId NOT IN (SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN CatalogueOptionValues cov ON optval.OptionValueId = cov.OptionValueId INNER JOIN Catalogue ON cov.CatalogueId = Catalogue.CatalogueId AND Catalogue.name NOT LIKE '%POSH%' UNION SELECT -1)
```

### DependencyManager.cs#17 — line 971
```sql
SELECT DISTINCT OptionValueId FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.ProductCategoryId = 1
```

### DependencyManager.cs#18 — line 998
```sql
SELECT DISTINCT optval.OptionValueId, opt.IsFabric, opt.Name + ' - ' + optval.Name + ' (' + optval.OrderCodeValue + ')' AS NamePair, optval.DisplayOrdinal FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.IsFabric = 1
```

### DependencyManager.cs#19 — line 1029
```sql
SELECT DISTINCT optval.OptionValueId, opt.IsFabric, opt.Name + ' - ' + optval.Name + ' (' + optval.OrderCodeValue + ')' AS NamePair, optval.DisplayOrdinal FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE optval.OrderCodeValue LIKE '%{text}%'
```

### DependencyManager.cs#20 — line 1063
```sql
SELECT DISTINCT atval.AttributeValueId, attr.Name + ' - ' + atval.Name + ' (' + atval.OrderCodeValue + ')' AS NamePair, attr.DisplayOrder, atval.DisplayOrdinal FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId INNER JOIN AttributeValue parent_atval ON parent_atval.AttributeValueId = {_parentAtValIds[parent_atvals.SelectedIndex].ToString()} INNER JOIN Attribute parent_attr ON parent_atval.AttributeId = parent_attr.AttributeId LEFT OUTER JOIN AttributeValueExclusions ave ON atval.AttributeValueId = ave.ExcludedAttributeValueId AND ave.AttributeValueId = {_parentAtValIds[parent_atvals.SelectedIndex].ToString()} WHERE attr.DisplayOrder > parent_attr.DisplayOrder AND attr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND atval.OrderCodeValue LIKE '%{text}%' AND ave.AttributeValueId IS NULL ORDER BY attr.DisplayOrder, atval.DisplayOrdinal
```

### DependencyManager.cs#21 — line 1329
```sql
DELETE FROM AttributeValueExclusions WHERE AttributeValueId = {_parentAtValIds[parent_atvals.SelectedIndex].ToString()} AND ExcludedAttributeValueId = {_inheritOptValIds[contextIndex].ToString()}
```

### DependencyManager.cs#22 — line 1340
```sql
DELETE FROM DependentAttributeValues WHERE AttributeValueId = {_parentAtValIds[parent_atvals.SelectedIndex].ToString()} AND AdditionalOptionValueId = {_inheritOptValIds[contextIndex].ToString()}
```

### DependencyManager.cs#23 — line 1345
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DependencyManager.cs#24 — line 1348
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DependencyManager.cs#25 — line 1357
```sql
INSERT INTO PDMAudit.dbo.DAVUpdates (TransactionId, AttributeValueId, AdditionalOptionValueId, ActionTaken) VALUES ({Conversions.ToString(num)}, {_parentAtValIds[parent_atvals.SelectedIndex].ToString()}, {_inheritOptValIds[contextIndex].ToString()}, 'REMOVED')
```

### DependencyManager.cs#26 — line 1370
```sql
DELETE FROM DependentOptionValues WHERE OptionValueId = {_parentOptValIds[parent_optvals.SelectedIndex].ToString()} AND AdditionalOptionValueId = {_inheritOptValIds[contextIndex].ToString()}
```

### DependencyManager.cs#27 — line 1375
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### DependencyManager.cs#28 — line 1378
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### DependencyManager.cs#29 — line 1387
```sql
INSERT INTO PDMAudit.dbo.DOVUpdates (TransactionId, OptionValueId, AdditionalOptionValueId, ActionTaken) VALUES ({Conversions.ToString(num2)}, {_parentOptValIds[parent_optvals.SelectedIndex].ToString()}, {_inheritOptValIds[contextIndex].ToString()}, 'REMOVED')
```

### DependencyManager.cs#30 — line 1495
```sql
DELETE FROM CatalogueProductOptionExclusions WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductId = {_productIds[parent_atvals.SelectedIndices[i]].ToString()} AND OptionValueId = {_excludeOptValIds[contextIndex].ToString()}
```

### DependencyManager.cs#31 — line 1508
```sql
DELETE FROM CatalogueProductOptionExclusions WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductId = {_productIds[parent_atvals.SelectedIndex].ToString()}
```

### DependencyManager.cs#32 — line 1632
```sql
SELECT DISTINCT Product.ProductId, Product.Product, cpoe.OptionValueId FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId AND pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = {Conversions.ToString(Global.catalogueId)} LEFT OUTER JOIN CatalogueProductOptionExclusions cpoe ON ci.CatalogueId = cpoe.CatalogueId AND cpoe.ProductId = Product.ProductId ORDER BY Product.Product
```

### DependencyManager.cs#33 — line 1658
```sql
SELECT atval.AttributeValueId, CASE WHEN atval.OrderCodeValue IS NOT NULL THEN attr.Name + ' - ' + atval.Name + ' (' + atval.OrderCodeValue + ')' ELSE attr.Name + ' - ' + atval.Name END AS NamePair FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 AND attr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND (atval.OrderCodeValue IS NOT NULL OR atval.ModelSuffix IS NOT NULL OR (attr.ProductCategoryId IN (611, 599, 607, 608, 615) And attr.DisplayOrder > 1) /* Stem categories with discrete products */
```

### DependencyManager.cs#34 — line 1678
```sql
SELECT ExcludedAttributeValueId FROM AttributeValueExclusions ave INNER JOIN AttributeValue atval ON ave.ExcludedAttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE Status = 1 And ave.AttributeValueId = {_parentAtValIds[i].ToString()} And attr.ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### DependencyManager.cs#35 — line 1695
```sql
SELECT AdditionalOptionValueId FROM DependentAttributeValues dav INNER JOIN OptionValue optval ON dav.AdditionalOptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE Status = 1 And dav.AttributeValueId = {_parentAtValIds[j].ToString()} And (opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)} Or opt.IsFabric = 1)
```

### DependencyManager.cs#36 — line 1714
```sql
SELECT optval.OptionValueId, opt.Name + ' - ' + optval.Name + ' (' + optval.OrderCodeValue + ')' AS NamePair FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE Status = 1 AND opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND (opt.IsFabric = 0 OR (opt.IsFabric = 1 AND opt.OptionId <> 8 AND opt.OptionId <> 3344)) AND opt.Name NOT LIKE '%fabric colour%'
```

### DependencyManager.cs#37 — line 1729
```sql
SELECT optval.OptionValueId, opt.Name + ' - ' + optval.Name + ' (' + optval.OrderCodeValue + ')' AS NamePair FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE Status = 1 AND opt.IsFabric = 1 ORDER BY opt.DisplayOrder, opt.Name, optval.DisplayOrdinal
```

### DependencyManager.cs#38 — line 1744
```sql
SELECT dov.AdditionalOptionValueId FROM DependentOptionValues dov INNER JOIN OptionValue optval ON dov.AdditionalOptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE Status = 1 AND dov.OptionValueId = {_parentOptValIds[k].ToString()} AND (opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)} OR opt.IsFabric = 1){) : (}SELECT cpoe.OptionValueId FROM CatalogueProductOptionExclusions cpoe INNER JOIN OptionValue optval ON cpoe.OptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE Status = 1 AND cpoe.OptionValueId = {_parentOptValIds[k].ToString()} AND (opt.ProductCategoryId = {Conversions.ToString(Global.categoryId)} OR opt.IsFabric = 1 OR opt.IsFabric = 2){))}
```

## GetLeadTime.cs  (8)

### GetLeadTime.cs#1 — line 134
```sql
SELECT Item.ItemId, Item.ProductId, Product.ProductRangeId, Product.OrderCodeFormatString AS prodFS, ProductRange.ProductCategoryId, ProductRange.OrderCodeFormatString AS rangeFS FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange ON Product.ProductRangeId = ProductRange.ProductRangeId INNER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId INNER JOIN Item sub_item ON itco.SubItemId = sub_item.ItemId INNER JOIN Product sub_product ON sub_item.ProductId = sub_product.ProductId WHERE sub_item.Item = '{text4}' AND sub_product.ProductRangeId = 999
```

### GetLeadTime.cs#2 — line 152
```sql
SELECT Item.ItemId, Item.ProductId, Product.ProductRangeId, Product.OrderCodeFormatString AS prodFS, ProductRange.ProductCategoryId, ProductRange.OrderCodeFormatString AS rangeFS FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange ON Product.ProductRangeId = ProductRange.ProductRangeId WHERE Item.Item = '{text4}' /*AND Product.ProductRangeId <> 999*/
```

### GetLeadTime.cs#3 — line 178
```sql
SELECT DISTINCT CatalogueId FROM CatalogueItems WHERE ItemId = {, arrayList2[i]))}
```

### GetLeadTime.cs#4 — line 216
```sql
SELECT Status FROM CatalogueProductCategories WHERE ProductCategoryId = {, arrayList5[i]),} AND CatalogueId = {), catalogueId))}
```

### GetLeadTime.cs#5 — line 234
```sql
SELECT LeadTime FROM Catalogue WHERE CatalogueId = {Conversions.ToString(catalogueId)}
```

### GetLeadTime.cs#6 — line 252
```sql
SELECT COUNT(*) AS cnt FROM CatalogueProductRanges WHERE ProductRangeId = {, arrayList4[i]),} AND CatalogueId = {), catalogueId))}
```

### GetLeadTime.cs#7 — line 267
```sql
SELECT bav.AttributeValueId AS atval, Attribute.AttributeType AS attrtype, Attribute.OrderCodeFormatKey AS attrkey FROM BaseAttributeValues bav INNER JOIN AttributeValue ON bav.AttributeValueId = AttributeValue.AttributeValueId INNER JOIN Attribute ON AttributeValue.AttributeId = Attribute.AttributeId WHERE ItemId = {, arrayList2[i]))}
```

### GetLeadTime.cs#8 — line 288
```sql
SELECT COUNT(*) AS cnt FROM CatalogueAttributeValues WHERE AttributeValueId = {, arrayList10[k]),} AND CatalogueId = {), catalogueId))}
```

## GetPrice.cs  (20)

### GetPrice.cs#1 — line 222
```sql
SELECT WeightKilos, VolumeLitres FROM Item WHERE Item = '{, data3.BaseItem[k]),}'{))}
```

### GetPrice.cs#2 — line 276
```sql
SELECT CASE WHEN od1.ShortDescription IS NULL THEN opt.Name ELSE od1.ShortDescription END AS optname, CASE WHEN od2.ShortDescription IS NULL THEN optval.Name ELSE od2.ShortDescription END AS optvalname, optval.OrderCodeValue FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId LEFT OUTER JOIN OtherDescription od1 ON opt.DescriptionId = od1.DescriptionId AND od1.LanguageId = {Conversions.ToString(Global.languageId)} LEFT OUTER JOIN OtherDescription od2 ON optval.DescriptionId = od2.DescriptionId AND od2.LanguageId = {Conversions.ToString(Global.languageId)} WHERE optval.OptionValueId = {, optvals[i])) : Conversions.ToString(Operators.ConcatenateObject(}SELECT opt.USOptionName AS optname, optval.USOptionValueName AS optvalname, optval.OrderCodeValue FROM USOptionValue optval INNER JOIN USOption opt ON optval.USOptionId = opt.USOptionId WHERE optval.USOptionValueId = {, optvals[i])))}
```

### GetPrice.cs#3 — line 342
```sql
SELECT SubItemId AS subitem_id FROM ItemComponents WHERE ItemId = {Conversions.ToString(myitemid)}
```

### GetPrice.cs#4 — line 357
```sql
SELECT pf.EffectiveDate AS min_date, (CAST(DATEDIFF(second, '1970-01-01', CAST(pf.EffectiveDate AS datetime)) AS bigint) * 1000) + DATEDIFF(ms, CAST(pf.EffectiveDate AS datetime), pf.EffectiveDate) AS msSinceEpoch FROM PriceFormula pf INNER JOIN PriceMatrix pm ON pf.PriceFormula = pm.PriceFormula INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(Global.currencyId)} INNER JOIN Product_Code pc ON pm.ItemPriceCode = pc.PriceCode AND pc.SiteId ={Conversions.ToString(Global.SiteId(allowPLCOverride: true))} INNER JOIN Product ON Product.ProductCodeId = pc.ProductCodeId INNER JOIN Item ON Product.ProductId = Item.ProductId WHERE Item.ItemId = '{, arrayList6[i]),}' AND pf.SiteId = {), Global.SiteId(allowPLCOverride: true)),} {),}ORDER BY pf.EffectiveDate{))}
```

### GetPrice.cs#5 — line 382
```sql
SELECT Item.Item, Item.WeightKilos, Item.VolumeLitres, parent_item.Item AS parent_item, Item.BasePrice AS base_price, Item.BasePrice2 AS base_price2, Item.BasePrice3 AS base_price3, itco.Quantity AS parent_qty, itco.FeaturePositionString, pc.Product_Code, pc.PriceCode AS price_code, pm.Rounding AS rounding, pc.BasePriceRef AS price_ref, dbo.fnGetListPrice(Currency.Currency, CASE WHEN pc.BasePriceRef = 2 THEN Item.BasePrice2 WHEN pc.BasePriceRef = 3 THEN Item.BasePrice3 ELSE Item.BasePrice END, pc.PriceCode, {text4}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS ListPrice, CASE WHEN od.ShortDescription IS NULL THEN component_product.Product ELSE od.ShortDescription END AS Description FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product component_product ON Item.ProductId = component_product.ProductId LEFT OUTER JOIN OtherDescription od ON component_product.DescriptionId = od.DescriptionId AND od.RelatedTable = 'SPComponent' AND od.LanguageId = 1 INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId INNER JOIN Item parent_item ON itco.ItemId = parent_item.ItemId INNER JOIN Product parent_product ON parent_item.ProductId = parent_product.ProductId INNER JOIN Product ON Item.ProductId = Product.ProductId {,}INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE component_product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, Conversions.ToString(Global.SiteId(allowPLCOverride: true)),} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {, Conversions.ToString(Global.currencyId),} WHERE Item.ItemId = {), arrayList6[j]),} AND itco.ItemId = {), myitemid),} AND Item.Status < 2 /* NOTE: we can resolve a price for active super products with URL components */ AND parent_item.Status = 1{))}
```

### GetPrice.cs#6 — line 482
```sql
SELECT dbo.fnGetListPrice(Currency.Currency, CASE WHEN pc.BasePriceRef = 2 THEN Item.BasePrice2 WHEN pc.BasePriceRef = 3 THEN Item.BasePrice3 ELSE Item.BasePrice END, pc.PriceCode, {text4}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS ListPrice FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product ON Item.ProductId = Product.ProductId {,}INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, Conversions.ToString(Global.SiteId(allowPLCOverride: true)),} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {, Conversions.ToString(Global.currencyId),} WHERE Item.ItemId = {, Conversions.ToString(myitemid))}
```

### GetPrice.cs#7 — line 496
```sql
SELECT Currency FROM Currency WHERE Currency_ID = {Conversions.ToString(Global.currencyId)}
```

### GetPrice.cs#8 — line 564
```sql
SELECT DISTINCT Item.ItemId, Item.Item, optval.OptionValueId, optval.OptionId, optval.OrderCodeValue, itov.IncrementalPrice, itov.IncrementalPrice2, itov.IncrementalPrice3, dbo.fnGetListPrice(Currency.Currency, CASE WHEN pc.BasePriceRef = 2 THEN itov.IncrementalPrice2 WHEN pc.BasePriceRef = 3 THEN itov.IncrementalPrice3 ELSE itov.IncrementalPrice END, pc.PriceCode, '{text11}', 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS IncPrice FROM Item INNER JOIN Product On Item.ProductId = Product.ProductId INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} INNER JOIN ItemOptionValues itov ON Item.ItemId = itov.ItemId INNER JOIN OptionValue optval ON itov.OptionValueId = optval.OptionValueId INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency = '{text10}' WHERE Item.Item = '{arrayList13[m].ToString()}' AND optval.OrderCodeValue = '{arrayList11[m].ToString()}' AND optval.OptionId = 3831
```

### GetPrice.cs#9 — line 639
```sql
SELECT 1 AS Quantity, -1 AS SubItemId, '' AS CompItem, opt.DisplayOrder, CASE WHEN opt.TertiaryOption > 0 AND opt.TertiaryOption < 20 THEN opt.TertiaryOption ELSE 0 END AS TertiaryOption, ov.OptionValueId, '' AS FeaturePositionString, ov.DisplayOrdinal, Item.Item, ov.OrderCodeValue AS order_code, ov.OptionId, itov.IncrementalPrice AS inc_price, itov.IncrementalPrice2 AS inc_price2, itov.IncrementalPrice3 AS inc_price3, pc.BasePriceRef AS price_ref, dbo.fnGetListPrice(Currency.Currency, CASE WHEN pc.BasePriceRef = 2 THEN itov.IncrementalPrice2 WHEN pc.BasePriceRef = 3 THEN itov.IncrementalPrice3 ELSE itov.IncrementalPrice END, pc.PriceCode, {text4}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS IncListPrice FROM ItemOptionValues itov CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN OptionValue ov ON itov.OptionValueId = ov.OptionValueId INNER JOIN [Option] opt ON ov.OptionId = opt.OptionId INNER JOIN Item ON itov.ItemId = Item.ItemId INNER JOIN Product ON Item.ProductId = Product.ProductId {,}INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, Conversions.ToString(Global.SiteId(allowPLCOverride: true)),} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {, Conversions.ToString(Global.currencyId),} WHERE Item.ItemId = {, Conversions.ToString(myitemid),} {) : (}SELECT 1 AS Quantity, -1 AS SubItemId, '' AS CompItem, 1 AS DisplayOrder, 0 AS TertiaryOption, optval.USOptionValueId AS OptionValueId, '' AS FeaturePositionString, optval.DisplayOrder AS DisplayOrdinal, USItem.USItem AS Item, optval.OrderCodeValue AS order_code, optval.USOptionId AS OptionId, uitov.IncrementalPrice AS inc_price, 1 AS price_ref, dbo.fnGetListPrice(Currency.Currency, uitov.IncrementalPrice, pc.PriceCode, {text4}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS IncListPrice FROM USItemOptionValues uitov INNER JOIN USOptionValue optval ON uitov.USOptionValueId = optval.USOptionValueId INNER JOIN USOption opt ON optval.USOptionId = opt.USOptionId INNER JOIN USItem ON uitov.USItemId = USItem.USItemId INNER JOIN /*US*/Product_Code pc ON USItem.Product_Code = pc.Product_Code AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(Global.currencyId)} WHERE USItem = '{myitem}' UNION SELECT 1 AS Quantity, -1 AS SubItemId, 1 AS DisplayOrder, 0 AS TertiaryOption, optval2.USOptionValueId AS OptionValueId, optval2.DisplayOrder AS DisplayOrdinal, USItem.USItem AS Item, optval2.OrderCodeValue AS order_code, optval2.USOptionId AS OptionId, udov.CommonIncrementalPrice AS inc_price, 1 AS price_ref, dbo.fnGetListPrice(Currency.Currency, udov.CommonIncrementalPrice, pc.PriceCode, {text4}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS IncListPrice FROM USItemOptionValues uitov INNER JOIN USOptionValue optval ON uitov.USOptionValueId = optval.USOptionValueId INNER JOIN USItem ON uitov.USItemId = USItem.USItemId INNER JOIN /*US*/Product_Code pc ON USItem.Product_Code = pc.Product_Code AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(Global.currencyId)} INNER JOIN USDependentOptionValues udov ON optval.USOptionValueId = udov.USOptionValueId INNER JOIN USOptionValue optval2 ON udov.USAdditionalOptionValueId = optval2.USOptionValueId INNER JOIN USOption opt2 ON optval2.USOptionId = opt2.USOptionId WHERE USItem = '{myitem}' {))}
```

### GetPrice.cs#10 — line 1110
```sql
SELECT CatalogueId, LeadTime, RIGHT('0000' + CONVERT(varchar, LeadTime), 4) + '_' + RIGHT('0000' + CONVERT(varchar, CASE WHEN PrimarySiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} THEN PrimarySiteId ELSE (PrimarySiteId * 10) END), 4) AS myorder FROM Catalogue WHERE CatalogueId IN (-1,
```

### GetPrice.cs#11 — line 1150
```sql
SELECT Currency FROM Currency WHERE Currency_ID = {Conversions.ToString(currencyId)}
```

### GetPrice.cs#12 — line 1158
```sql
SELECT Product.Product, Product.ProductCodeId, ProductCategory.Name AS category_name, Item.ItemId, Item.Status, Item.ProductId, Item.BasePrice AS base_price, Item.BasePrice2 AS base_price2, Item.BasePrice3 AS base_price3, Product.IsSuperProduct, Product.OrderCodeFormatString AS prodFS, pc.PriceCode AS price_code, pm.Rounding AS rounding, pc.BasePriceRef AS price_ref, ProductRange.ProductRangeId, ProductRange.ProductCategoryId, ProductRange.OrderCodeFormatString AS rangeFS FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange ON Product.ProductRangeId = ProductRange.ProductRangeId INNER JOIN ProductCategory ON ProductRange.ProductCategoryId = ProductCategory.ProductCategoryId LEFT OUTER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} LEFT OUTER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode LEFT OUTER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(currencyId)} WHERE Item.Item = '{text4}' /*AND Product.ProductRangeId <> 999*/{) : (}SELECT USItem.USItem AS Product, -1 AS ProductCodeId, 'US Data' AS category_name, USItem.USItemId AS ItemId, 1 AS Status, -1 AS ProductId, USItem.BasePrice AS base_price, 'False' AS IsSuperProduct, NULL AS prodFS, pc.PriceCode AS price_code, pm.Rounding AS rounding, pc.BasePriceRef AS price_ref, 512 AS ProductRangeId, USItem.ProductCategoryId, NULL AS rangeFS FROM USItem INNER JOIN /*US*/Product_Code pc ON USItem.Product_Code = pc.Product_Code AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(currencyId)} WHERE USItem = '{text4}'{))}
```

### GetPrice.cs#13 — line 1248
```sql
SELECT atval.AttributeValueId AS atvalId, attr.OrderCodeFormatKey AS attrkey, attr.AttributeType AS attrtype, CASE WHEN od1.ShortDescription IS NULL THEN attr.Name ELSE od1.ShortDescription END AS attrname, CASE WHEN od2.ShortDescription IS NULL THEN atval.Name ELSE od2.ShortDescription END AS atvalname FROM BaseAttributeValues bav INNER JOIN AttributeValue atval ON bav.AttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId LEFT OUTER JOIN OtherDescription od1 ON attr.DescriptionId = od1.DescriptionId AND od1.LanguageId = {Conversions.ToString(Global.languageId)} LEFT OUTER JOIN OtherDescription od2 ON atval.DescriptionId = od2.DescriptionId AND od2.LanguageId = {Conversions.ToString(Global.languageId)} WHERE ItemId = {Conversions.ToString(num5)) ??}
```

### GetPrice.cs#14 — line 1279
```sql
SELECT COUNT(*) AS cnt FROM CatalogueAttributeValues WHERE AttributeValueId = {, arrayList3[k]),} AND CatalogueId = {), catalogueId))}
```

### GetPrice.cs#15 — line 1359
```sql
SELECT Catalogue.CatalogueId, Catalogue.LeadTime FROM CatalogueItems ci INNER JOIN Item ON ci.ItemId = Item.ItemId INNER JOIN Catalogue ON ci.CatalogueId = Catalogue.CatalogueId WHERE Item.Item = '{text4}' ORDER BY Catalogue.LeadTime
```

### GetPrice.cs#16 — line 1461
```sql
SELECT Description, Product_Code FROM USItem WHERE USItem = '{text4}'
```

### GetPrice.cs#17 — line 1527
```sql
SELECT LeadTimeOffset FROM SiteCatalogues WHERE SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### GetPrice.cs#18 — line 1538
```sql
SELECT Product_Code.Product_Code AS prod_code, pc.Name AS category_name, (CASE WHEN ProductDescription.ShortDescription IS NULL OR {Conversions.ToString(Global.languageId)} = 1 THEN Product.Name ELSE ProductDescription.ShortDescription END) AS prod_name, Product.ImageFile, Product.WFImageFile AS wf_image, ProductDescription.LongDescription AS long_desc, Product.IsSuperProduct, ProductRange.ProductCategoryId FROM Product INNER JOIN ProductRange ON Product.ProductRangeId = ProductRange.ProductRangeId INNER JOIN ProductCategory pc ON ProductRange.ProductCategoryId = pc.ProductCategoryId LEFT OUTER JOIN Product_Code ON Product.ProductCodeId = Product_Code.ProductCodeId AND Product_Code.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} LEFT OUTER JOIN ProductDescription ON Product.DescriptionId = ProductDescription.DescriptionId AND ProductDescription.LanguageId = {Conversions.ToString(Global.languageId)} WHERE Product.ProductId = {Conversions.ToString(num4)}
```

### GetPrice.cs#19 — line 1619
```sql
SELECT WeightKilos, VolumeLitres FROM Item WHERE ItemId = {Conversions.ToString(num5)}
```

### GetPrice.cs#20 — line 1693
```sql
SELECT OrderType FROM Catalogue WHERE CatalogueId = {, myQuoteData.CatalogueId[num37]))}
```

## GetPriceExt.cs  (4)

### GetPriceExt.cs#1 — line 131
```sql
SELECT pf.EffectiveDate AS min_date, (CAST(DATEDIFF(second, '1970-01-01', CAST(pf.EffectiveDate AS datetime)) AS bigint) * 1000) + DATEDIFF(ms, CAST(pf.EffectiveDate AS datetime), pf.EffectiveDate) AS msSinceEpoch FROM PriceFormula pf INNER JOIN PriceMatrix pm ON pf.PriceFormula = pm.PriceFormula INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(Global.currencyId)} INNER JOIN Product_Code pc ON pm.ItemPriceCode = pc.PriceCode AND pc.SiteId ={Conversions.ToString(Global.SiteId(allowPLCOverride: true))} INNER JOIN Product ON Product.ProductCodeId = pc.ProductCodeId INNER JOIN Item ON Product.ProductId = Item.ProductId WHERE Item.Item = '{text}' AND pf.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} AND pf.EffectiveDate <= GetUTCDate() ORDER BY pf.EffectiveDate
```

### GetPriceExt.cs#2 — line 153
```sql
SELECT Site FROM Site WHERE SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}
```

### GetPriceExt.cs#3 — line 161
```sql
SELECT Currency FROM Currency WHERE Currency_ID = {Conversions.ToString(Global.currencyId)}
```

### GetPriceExt.cs#4 — line 170
```sql
SELECT Product.Product, ProductCategory.Name AS category_name, Currency.Currency, Item.ItemId, Item.Status, Item.ProductId, Item.BasePrice AS base_price, Item.BasePrice2 AS base_price2, Item.BasePrice3 AS base_price3, Product.IsSuperProduct, Product.OrderCodeFormatString AS prodFS, dbo.fnGetListPrice(Currency.Currency, CASE WHEN pc.BasePriceRef = 2 THEN Item.BasePrice2 WHEN pc.BasePriceRef = 3 THEN Item.BasePrice3 ELSE Item.BasePrice END, pc.PriceCode, {text4}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS ListPrice, pc.PriceCode AS price_code, pm.Rounding AS rounding, pc.BasePriceRef AS price_ref, ProductRange.ProductRangeId, ProductRange.ProductCategoryId, ProductRange.OrderCodeFormatString AS rangeFS FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange ON Product.ProductRangeId = ProductRange.ProductRangeId INNER JOIN ProductCategory ON ProductRange.ProductCategoryId = ProductCategory.ProductCategoryId {,}INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, Conversions.ToString(Global.SiteId(allowPLCOverride: true)),} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {, Conversions.ToString(Global.currencyId),} WHERE Item.Item = '{, text,}'{)}
```

## HermanMiller.EOS.UI\AttributeSelector.cs  (9)

### HermanMiller.EOS.UI\AttributeSelector.cs#1 — line 120
```sql
SELECT dbo.AttributeValue.OrderCodeValue AS code_value FROM dbo.AttributeValue WHERE dbo.AttributeValue.AttributeValueId = {Conversions.ToString(AttributeValueId)}
```

### HermanMiller.EOS.UI\AttributeSelector.cs#2 — line 265
```sql
SELECT DISTINCT attr.DisplayOrder, attr.Name AS attr_name FROM Attribute attr WHERE attr.AttributeId = {Conversions.ToString(num5)}
```

### HermanMiller.EOS.UI\AttributeSelector.cs#3 — line 306
```sql
SELECT DISTINCT CASE WHEN od.ShortDescription IS NULL THEN atval.Name ELSE od.ShortDescription END AS atval_name FROM Attribute attr INNER JOIN AttributeValue atval ON attr.AttributeId = atval.AttributeId INNER JOIN CatalogueAttributeValues cav ON atval.AttributeValueId = cav.AttributeValueId AND cav.CatalogueId = {Conversions.ToString(Global.catalogueId)} LEFT OUTER JOIN OtherDescription od ON atval.DescriptionId = od.DescriptionId AND od.LanguageId = {Conversions.ToString(Global.languageId)} WHERE attr.AttributeId = {Conversions.ToString(AttributeId)}
```

### HermanMiller.EOS.UI\AttributeSelector.cs#4 — line 394
```sql
SELECT AttributeId FROM USAttribute WHERE AttributeId = {Conversions.ToString(attributeId)}
```

### HermanMiller.EOS.UI\AttributeSelector.cs#5 — line 436
```sql
SELECT DISTINCT ExcludedAttributeValueId FROM AttributeValueExclusions WHERE AttributeValueId IN (
```

### HermanMiller.EOS.UI\AttributeSelector.cs#6 — line 757
```sql
SELECT Attribute.AttributeType AS attrtype FROM Attribute INNER JOIN AttributeValue ON AttributeValue.AttributeId = Attribute.AttributeId WHERE Attribute.AttributeId = {Conversions.ToString(attrid)}
```

### HermanMiller.EOS.UI\AttributeSelector.cs#7 — line 768
```sql
SELECT OptionValue.OptionId AS opt_id FROM OptionValue INNER JOIN DependentAttributeValues ON OptionValue.OptionValueId = DependentAttributeValues.AdditionalOptionValueId INNER JOIN AttributeValue ON DependentAttributeValues.AttributeValueId = AttributeValue.AttributeValueId WHERE AttributeValue.AttributeId = {Conversions.ToString(attrid)}
```

### HermanMiller.EOS.UI\AttributeSelector.cs#8 — line 783
```sql
SELECT optval.OptionId FROM CatalogueItemOptionExclusions cioe INNER JOIN OptionValue optval ON cioe.OptionValueId = optval.OptionValueId WHERE cioe.CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### HermanMiller.EOS.UI\AttributeSelector.cs#9 — line 795
```sql
SELECT ave.AttributeValueId FROM AttributeValueExclusions ave INNER JOIN AttributeValue atval ON ave.AttributeValueId = atval.AttributeValueId WHERE atval.AttributeId = {Conversions.ToString(attrid)}
```

## HermanMiller.EOS.UI\ImageButton.cs  (1)

### HermanMiller.EOS.UI\ImageButton.cs#1 — line 118
```sql
SELECT Product.Name, Product.Product, Product.ImageFile, CASE WHEN cat.ApplicationText IS NOT NULL THEN cat.ApplicationText ELSE pd.ApplicationText END AS ApplicationText FROM Product INNER JOIN ProductDescription pd ON Product.DescriptionId = pd.DescriptionId LEFT OUTER JOIN CatalogueApplicationText cat ON Product.ProductId = cat.ProductId AND cat.CatalogueId = {Conversions.ToString(Global.catalogueId)} AND cat.LanguageId = {Conversions.ToString(Global.languageId)} WHERE Product.ProductId = {Conversions.ToString(Global.productId)} AND pd.LanguageId = {Conversions.ToString(Global.languageId)}
```

## HermanMiller.EOS.UI\ImageButtonList.cs  (2)

### HermanMiller.EOS.UI\ImageButtonList.cs#1 — line 206
```sql
SELECT USItem FROM USItem WHERE USItem.USItemId = {Conversions.ToString(id)}
```

### HermanMiller.EOS.UI\ImageButtonList.cs#2 — line 361
```sql
SELECT Product.Name AS prod_name, Product.Product AS prod_code, Product.ProductId AS prod_id, pc.Product_Code FROM Product INNER JOIN /*root*/Product_Code pc ON Product.ProductCodeId = pc.ProductCodeId AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} WHERE ProductId = {imageButton.Tag.ToString()) : (}SELECT USItem.Description AS prod_name, USItem.USItem AS prod_code, USItem.USItemId AS prod_id, pc.Product_Code FROM USItem INNER JOIN /*US*/Product_Code pc ON USItem.Product_Code = pc.Product_Code WHERE USItem.USItemId = {imageButton.Tag.ToString()} AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))))}
```

## HermanMiller.EOS.UI\OptionSelector.cs  (11)

### HermanMiller.EOS.UI\OptionSelector.cs#1 — line 103
```sql
SELECT IsFabric FROM [Option] WHERE OptionId = {Conversions.ToString(OptionId)}
```

### HermanMiller.EOS.UI\OptionSelector.cs#2 — line 266
```sql
SELECT optval.USOptionValueId, optval.USOptionValueName, NULL AS ParentId, NULL AS ImageFile, 1 AS Available, optval.OrderCodeValue, optval.DisplayOrder FROM USOptionValue optval INNER JOIN USOption opt ON optval.USOptionId = opt.USOptionId INNER JOIN USItemOptionValues itov ON optval.USOptionValueId = itov.USOptionValueId INNER JOIN USItem ON itov.USItemId = USItem.USItemId WHERE USItem.USItemId = {Conversions.ToString(Global.productId)} AND opt.OptionId = {Conversions.ToString(OptionId)}
```

### HermanMiller.EOS.UI\OptionSelector.cs#3 — line 381
```sql
SELECT ov.OptionValueId, ov.OptionId, ov.AssociatedDefault, CASE WHEN od.ShortDescription IS NULL THEN ov.Name ELSE od.ShortDescription END + CASE WHEN ov.SupplierCode IS NULL THEN '' ELSE ' (' + ov.SupplierCode + ')' END + CASE WHEN ov.OrderCodeValue IS NULL THEN '' ELSE ' - ' + ov.OrderCodeValue END AS short_desc, ov.OrderCodeValue, ov.DisplayOrdinal, ov.ImageFile, CASE WHEN a.OptionValueId IS NULL THEN 0 ELSE 1 END AS Available FROM OptionValue ov
```

### HermanMiller.EOS.UI\OptionSelector.cs#4 — line 631
```sql
SELECT OptionValueId FROM CatalogueItemOptionExclusions WHERE ItemId = {Conversions.ToString(currentItemId)} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### HermanMiller.EOS.UI\OptionSelector.cs#5 — line 1032
```sql
SELECT OptionId FROM CADDefaults WHERE (OptionId = {Conversions.ToString(sendOption)} AND ProductCategoryId = '{Conversions.ToString(_mycontainer.ProductCategoryId)}')
```

### HermanMiller.EOS.UI\OptionSelector.cs#6 — line 1051
```sql
SELECT DISTINCT optval.OptionValueId, dov.AdditionalOptionValueId, child.OrderCodeValue, child.OptionId, optval.OrderCodeValue AS ParentOptionValueCode FROM DependentOptionValues dov INNER JOIN OptionValue optval ON dov.OptionValueId = optval.OptionValueId INNER JOIN OptionValue child ON dov.AdditionalOptionValueId = child.OptionValueId WHERE optval.OptionId = {Conversions.ToString(sendOption)}
```

### HermanMiller.EOS.UI\OptionSelector.cs#7 — line 1060
```sql
SELECT OrderCodeValue FROM CADSchemeValues WHERE OptionId = {, sqlDataReader2[}OptionId{]),} AND ProductCategoryId = {), _mycontainer.ProductCategoryId),} AND SchemeKey = {), _mycontainer.CADTemplateSchemeKey))}
```

### HermanMiller.EOS.UI\OptionSelector.cs#8 — line 1082
```sql
SELECT OrderCodeValue FROM CADSchemeValues WHERE OptionId IN ({text}) AND ProductCategoryId = {Conversions.ToString(_mycontainer.ProductCategoryId)} AND SchemeKey = {Conversions.ToString(_mycontainer.CADTemplateSchemeKey)}
```

### HermanMiller.EOS.UI\OptionSelector.cs#9 — line 1167
```sql
SELECT DISTINCT dep_opt.usoptionname, dep_opt.OptionId AS opt_id FROM USOptionValue optval INNER JOIN USDependentOptionValues udov ON optval.USOptionValueId = udov.USOptionValueId INNER JOIN USOptionValue dep_optval ON udov.USAdditionalOptionValueId = dep_optval.USOptionValueId INNER JOIN USOption dep_opt ON dep_optval.USOptionId = dep_opt.USOptionId WHERE optval.USOptionValueId = {Conversions.ToString(optvalid)}
```

### HermanMiller.EOS.UI\OptionSelector.cs#10 — line 1194
```sql
SELECT DISTINCT optval1.OptionId AS opt_id FROM OptionValue optval1 INNER JOIN DependentOptionValues dov ON optval1.OptionValueId = dov.AdditionalOptionValueId INNER JOIN OptionValue optval2 ON dov.OptionValueId = optval2.OptionValueId INNER JOIN [Option] opt ON optval2.OptionId = opt.OptionId INNER JOIN OptionValue optval3 ON opt.OptionId = optval3.OptionId WHERE optval3.OptionValueId = {Conversions.ToString(optvalid)}
```

### HermanMiller.EOS.UI\OptionSelector.cs#11 — line 1202
```sql
SELECT DISTINCT associated_optval.OptionId FROM OptionValue optval INNER JOIN OptionValue associated_optval ON optval.AssociatedDefault = associated_optval.OptionValueId WHERE optval.OptionValueId = {Conversions.ToString(optvalid)}
```

## HermanMiller.EOS.UI\PreviousSelection.cs  (1)

### HermanMiller.EOS.UI\PreviousSelection.cs#1 — line 240
```sql
SELECT od.ShortDescription FROM OtherDescription od INNER JOIN DPSText ON od.DescriptionId = DPSText.DescriptionId WHERE DPSText.Description = 'Qty' AND LanguageId = {Conversions.ToString(Global.languageId)}
```

## HermanMiller.EOS.UI\ProductSelector.cs  (1)

### HermanMiller.EOS.UI\ProductSelector.cs#1 — line 165
```sql
SELECT pc.USCategory FROM ProductCategory pc INNER JOIN ProductRange pr ON pc.ProductCategoryId = pr.ProductCategoryId WHERE pr.ProductRangeId = {Conversions.ToString(productRangeId)}
```

## HermanMiller.EOS.UI\RangeSelector.cs  (1)

### HermanMiller.EOS.UI\RangeSelector.cs#1 — line 145
```sql
SELECT pr.ProductRangeId, (CASE WHEN od.ShortDescription IS NULL THEN pr.Name ELSE od.ShortDescription END) AS short_desc, pr.ProductCategoryId, pr.Status FROM ProductRange pr INNER JOIN CatalogueProductRanges cpr ON pr.ProductRangeId = cpr.ProductRangeId LEFT OUTER JOIN OtherDescription od ON pr.DescriptionId = od.DescriptionId AND od.LanguageId = {Conversions.ToString(Global.languageId)} WHERE (pr.ProductCategoryId = {Conversions.ToString(productCategoryId)} OR pr.ProductCategoryId = {Conversions.ToString(num)}) AND cpr.CatalogueId = {Conversions.ToString(catalogueId)}
```

## HermanMiller.EOS.UI\SwatchBox.cs  (5)

### HermanMiller.EOS.UI\SwatchBox.cs#1 — line 178
```sql
SELECT ShortDescription FROM OtherDescription INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 4 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### HermanMiller.EOS.UI\SwatchBox.cs#2 — line 230
```sql
SELECT ov.OptionValueId, ov.OptionId, (CASE WHEN od.ShortDescription IS NULL THEN ov.Name ELSE od.ShortDescription END) AS short_desc, ov.OrderCodeValue, ov.DisplayOrdinal, ov.ImageFile FROM OptionValue ov INNER JOIN DependentOptionValues dov ON ov.OptionValueId = dov.AdditionalOptionValueId INNER JOIN CatalogueOptionValues cov ON ov.OptionValueId = cov.OptionValueId INNER JOIN OtherDescription od ON ov.DescriptionId = od.DescriptionId INNER JOIN WHERE dov.OptionValueId = {Conversions.ToString(myOptionValueId)} AND cov.CatalogueId = {Conversions.ToString(myCatalogueId)} AND od.LanguageId = {Conversions.ToString(Global.languageId)}
```

### HermanMiller.EOS.UI\SwatchBox.cs#3 — line 234
```sql
SELECT DISTINCT ov.OptionValueId, ov.OptionId, (CASE WHEN od.ShortDescription IS NULL THEN ov.Name ELSE od.ShortDescription END) AS short_desc, ov.OrderCodeValue, ov.DisplayOrdinal, ov.ImageFile FROM OptionValue ov INNER JOIN [Option] opt ON ov.OptionId = opt.OptionId INNER JOIN CatalogueOptionValues cov ON ov.OptionValueId = cov.OptionValueId INNER JOIN OtherDescription od ON ov.DescriptionId = od.DescriptionId INNER JOIN WHERE opt.OptionId = {Conversions.ToString(baseOptionValueId * -1)} AND cov.CatalogueId = {Conversions.ToString(myCatalogueId)} AND od.LanguageId = {Conversions.ToString(Global.languageId)}
```

### HermanMiller.EOS.UI\SwatchBox.cs#4 — line 250
```sql
SELECT AdditionalOptionValueId FROM DependentAttributeValues WHERE AdditionalOptionValueId = {arrayList[i].ToString()}
```

### HermanMiller.EOS.UI\SwatchBox.cs#5 — line 263
```sql
SELECT AdditionalOptionValueId FROM DependentAttributeValues WHERE AttributeValueId IN (
```

## HermanMiller.EOS.UI\TemplateContainer.cs  (26)

### HermanMiller.EOS.UI\TemplateContainer.cs#1 — line 532
```sql
SELECT OptionId FROM OptionValue WHERE OptionValueId = {Conversions.ToString(selectedId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#2 — line 708
```sql
SELECT AttributeId FROM AttributeValue WHERE AttributeValueId = {Conversions.ToString(selectedId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#3 — line 919
```sql
SELECT USCategory FROM ProductCategory WHERE ProductCategoryId = {Conversions.ToString(categoryId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#4 — line 1181
```sql
SELECT (CASE WHEN od1.ShortDescription IS NULL OR {Conversions.ToString(Global.languageId)} = 1 THEN Attribute.Name ELSE od1.ShortDescription END) AS attr_name, (CASE WHEN od2.ShortDescription IS NULL OR {Conversions.ToString(Global.languageId)} = 1 THEN AttributeValue.Name ELSE od2.ShortDescription END) AS attrval_name FROM Attribute INNER JOIN AttributeValue ON Attribute.AttributeId = AttributeValue.AttributeId INNER JOIN OtherDescription od1 ON Attribute.DescriptionId = od1.DescriptionId INNER JOIN OtherDescription od2 ON AttributeValue.DescriptionId = od2.DescriptionId WHERE AttributeValue.AttributeValueId = {, NewLateBinding.LateGet(attrSelectors[i], null,}AttributeValueId{, new object[0], null, null, null)),} AND Attribute.AttributeType = 1 AND od1.LanguageId = {), Global.languageId),} AND od2.LanguageId = {), Global.languageId))}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#5 — line 1204
```sql
SELECT (CASE WHEN od1.ShortDescription IS NULL OR {Conversions.ToString(Global.languageId)} = 1 THEN [Option].Name ELSE od1.ShortDescription END) AS opt_name, (CASE WHEN od2.ShortDescription IS NULL OR {Conversions.ToString(Global.languageId)} = 1 THEN OptionValue.Name ELSE od2.ShortDescription END) AS optval_name FROM [Option] INNER JOIN OptionValue ON [Option].OptionId = OptionValue.OptionId INNER JOIN OtherDescription od1 ON [Option].DescriptionId = od1.DescriptionId INNER JOIN OtherDescription od2 ON OptionValue.DescriptionId = od2.DescriptionId WHERE OptionValue.OptionValueId = {, NewLateBinding.LateGet(optSelectors[j], null,}OptionValueId{, new object[0], null, null, null)),} AND od1.LanguageId = {), Global.languageId),} AND od2.LanguageId = {), Global.languageId))}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#6 — line 1244
```sql
SELECT pc.Product_Code FROM Product_Code pc INNER JOIN Product ON pc.ProductCodeId = Product.ProductCodeId WHERE Product.ProductId = {Conversions.ToString(productId)} AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))) : (}SELECT pc.Product_Code FROM Product_Code pc INNER JOIN USItem ON pc.Product_Code = USItem.Product_Code WHERE USItem.USItemId = {Conversions.ToString(productId)} AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))))}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#7 — line 1455
```sql
SELECT OptionValueId FROM FabricBands WHERE Application = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} AND PriceBand > 1
```

### HermanMiller.EOS.UI\TemplateContainer.cs#8 — line 1480
```sql
SELECT USItem.USItem AS prod_code, USItem.Description AS prod_name, USItem.USItemId AS item_id, USItem.USItem AS item_name, dbo.fnGetListPrice(Currency.Currency, USItem.BasePrice, pc.PriceCode, {text5}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS ListPrice, USItem.BasePrice AS base_price, pc.PriceCode AS price_code, pm.Rounding AS rounding, pc.BasePriceRef AS price_ref FROM USItem INNER JOIN /*US*/Product_Code pc ON USItem.Product_Code = pc.Product_Code AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(Global.currencyId)} WHERE USItemId = {Conversions.ToString(ProductId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#9 — line 1485
```sql
SELECT DISTINCT Product.IsSuperProduct AS super, Product.Product AS myprod, pr.ProductMaskKey, itco.FeaturePositionString FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId LEFT OUTER JOIN Item ON Product.ProductId = Item.ProductId LEFT OUTER JOIN ItemComponents itco ON Item.ItemId = itco.ItemId WHERE Product.ProductId = {Conversions.ToString(ProductId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#10 — line 1577
```sql
SELECT dbo.fnGetListPrice(Currency.Currency, {num9.ToString().Replace(},{,}.{)}, pc.PriceCode, {text5}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS ListPrice FROM Product_Code pc INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(Global.currencyId)} WHERE pc.ProductCodeId = {Conversions.ToString(num10)} AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#11 — line 1595
```sql
SELECT SubItemId AS subitem_id FROM ItemComponents WHERE ItemId = {text4}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#12 — line 1606
```sql
SELECT Item.BasePrice AS base_price, Item.BasePrice2 AS base_price2, Item.BasePrice3 AS base_price3, itco.Quantity AS sub_qty, dbo.fnGetListPrice(Currency.Currency, CASE WHEN pc.BasePriceRef = 2 THEN Item.BasePrice2 WHEN pc.BasePriceRef = 3 THEN Item.BasePrice3 ELSE Item.BasePrice END, pc.PriceCode, {text5}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS ListPrice, pc.PriceCode AS price_code, pm.Rounding AS rounding, pc.BasePriceRef AS price_ref FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId INNER JOIN Item parent_item ON itco.ItemId = parent_item.ItemId INNER JOIN Product ON Item.ProductId = Product.ProductId {,}INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, Conversions.ToString(Global.SiteId(allowPLCOverride: true)),} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {, Conversions.ToString(Global.currencyId),} WHERE Item.ItemId = {), arrayList9[k]),} AND itco.ItemId = {), text4),} AND Item.Status = 1 AND parent_item.Status = 1{))}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#13 — line 1717
```sql
SELECT DISTINCT 1 AS Quantity, -1 AS SubItemId, '' AS CompItem, Item.ItemId, Item.Item, pr.ProductMaskKey, pr.ProductRangeId, CASE WHEN itov.IncrementalPrice IS NULL THEN 0 ELSE itov.IncrementalPrice END AS inc_price, CASE WHEN itov.IncrementalPrice2 IS NULL THEN 0 ELSE itov.IncrementalPrice2 END AS inc_price2, CASE WHEN itov.IncrementalPrice3 IS NULL THEN 0 ELSE itov.IncrementalPrice3 END AS inc_price3, ov.OptionValueId, ov.OrderCodeValue, ov.Name AS Expr1, pc.BasePriceRef AS price_ref, ov.OptionId, Item.Status, dbo.fnGetListPrice(Currency.Currency, CASE WHEN pc.BasePriceRef = 2 THEN itov.IncrementalPrice2 WHEN pc.BasePriceRef = 3 THEN itov.IncrementalPrice3 ELSE itov.IncrementalPrice END, pc.PriceCode, {text5}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS IncListPrice, -1 AS AltOptId, -1 AS AltOptvalId FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN ItemOptionValues itov ON Item.ItemId = itov.ItemId INNER JOIN OptionValue ov ON itov.OptionValueId = ov.OptionValueId INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId {,}INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, Conversions.ToString(Global.SiteId(allowPLCOverride: true)),} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {, Conversions.ToString(Global.currencyId),} WHERE Item.ItemId = {, text4,} AND ov.OptionValueId = {, arrayList10[num19].ToString()) : (}SELECT DISTINCT 1 AS Quantity, -1 AS SubItemId, '' AS CompItem, 1 AS DisplayOrder, optval.DisplayOrder AS DisplayOrdinal, USItem.USItem AS Item, '' AS ProductMaskKey, optval.OrderCodeValue AS order_code, optval.USOptionId AS OptionId, uitov.IncrementalPrice AS inc_price, 1 AS price_ref, optval.USOptionValueId AS OptionValueId, dbo.fnGetListPrice(Currency.Currency, uitov.IncrementalPrice, pc.PriceCode, {text5}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS IncListPrice FROM USItemOptionValues uitov INNER JOIN USOptionValue optval ON uitov.USOptionValueId = optval.USOptionValueId INNER JOIN USOption opt ON optval.USOptionId = opt.USOptionId INNER JOIN USItem ON uitov.USItemId = USItem.USItemId INNER JOIN /*US*/Product_Code pc ON USItem.Product_Code = pc.Product_Code AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(Global.currencyId)} WHERE USItem.USItemId = {Conversions.ToString(ProductId)} AND optval.USOptionValueId = {arrayList10[num19].ToString()}UNION SELECT DISTINCT 1 AS Quantity, -1 AS SubItemId, 1 AS DisplayOrder, optval2.DisplayOrder AS DisplayOrdinal, USItem.USItem AS Item, '' AS ProductMaskKey, optval2.OrderCodeValue AS order_code, optval2.USOptionId AS OptionId, udov.CommonIncrementalPrice AS inc_price, 1 AS price_ref, optval.USOptionValueId AS OptionValueId, dbo.fnGetListPrice(Currency.Currency, udov.CommonIncrementalPrice, pc.PriceCode, {text5}, 'DMY', pm.Rounding, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}, NULL) AS IncListPrice FROM USItemOptionValues uitov INNER JOIN USOptionValue optval ON uitov.USOptionValueId = optval.USOptionValueId INNER JOIN USItem ON uitov.USItemId = USItem.USItemId INNER JOIN USDependentOptionValues udov ON optval.USOptionValueId = udov.USOptionValueId INNER JOIN USOptionValue optval2 ON udov.USAdditionalOptionValueId = optval2.USOptionValueId INNER JOIN USOption opt2 ON optval2.USOptionId = opt2.USOptionId INNER JOIN /*US*/Product_Code pc ON USItem.Product_Code = pc.Product_Code AND pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency_ID = {Conversions.ToString(Global.currencyId)} WHERE USItem.USItemId = {Conversions.ToString(ProductId)} AND optval2.USOptionValueId = {arrayList10[num19].ToString()))}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#14 — line 1888
```sql
SELECT SubItemId AS subitem_id FROM ItemComponents WHERE ItemId = {, TextCompare: false) == 0)
 {
 text10 = text10} [Additional Notes] {text3} Please check that the following conditions have been satisfied: 1) The SuperProduct flag is set to TRUE for this Product as required 2) An Item exists for this configuration in the Item table 3) The ItemComponents table has been populated for this Item If all of the above criteria have been met, the BaseAttributeValues data for this Item is either invalid or incomplete as the data cannot currently be resolved
```

### HermanMiller.EOS.UI\TemplateContainer.cs#15 — line 1936
```sql
SELECT DISTINCT Item.ItemId FROM Item
```

### HermanMiller.EOS.UI\TemplateContainer.cs#16 — line 2220
```sql
SELECT DISTINCT OptionId FROM [Option] WHERE IsFabric = 2 AND Name NOT LIKE '%Pellicle%'
```

### HermanMiller.EOS.UI\TemplateContainer.cs#17 — line 2816
```sql
SELECT ShortDescription FROM OtherDescription od INNER JOIN CatalogueProductCategories cpc ON od.DescriptionId = cpc.DescriptionId WHERE od.LanguageId = {Conversions.ToString(Global.languageId)} AND cpc.CatalogueId = {Conversions.ToString(Global.catalogueId)} AND cpc.ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#18 — line 2883
```sql
SELECT od.ShortDescription FROM OtherDescription od INNER JOIN DPSText ON od.DescriptionId = DPSText.DescriptionId WHERE DPSText.Description = 'Range' AND LanguageId = {Conversions.ToString(Global.languageId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#19 — line 2900
```sql
SELECT ShortDescription FROM OtherDescription od INNER JOIN Attribute attr ON od.DescriptionId = attr.DescriptionId WHERE od.LanguageId = {Conversions.ToString(Global.languageId)} AND attr.AttributeId = {Conversions.ToString(attributeSelector2.AttributeId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#20 — line 2917
```sql
SELECT ShortDescription FROM OtherDescription od INNER JOIN [Option] opt ON od.DescriptionId = opt.DescriptionId WHERE od.LanguageId = {Conversions.ToString(Global.languageId)} AND opt.OptionId = {Conversions.ToString(optionSelector2.OptionId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#21 — line 3271
```sql
SELECT ShortDescription FROM OtherDescription od INNER JOIN CatalogueProductCategories cpc ON od.DescriptionId = cpc.DescriptionId WHERE od.LanguageId = {Conversions.ToString(Global.languageId)} AND cpc.CatalogueId = {Conversions.ToString(Global.catalogueId)} AND cpc.ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#22 — line 3306
```sql
SELECT od.ShortDescription FROM OtherDescription od INNER JOIN DPSText ON od.DescriptionId = DPSText.DescriptionId WHERE DPSText.Description = 'Range' AND LanguageId = {Conversions.ToString(Global.languageId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#23 — line 3324
```sql
SELECT ShortDescription FROM OtherDescription od INNER JOIN Attribute attr ON od.DescriptionId = attr.DescriptionId WHERE od.LanguageId = {Conversions.ToString(Global.languageId)} AND attr.AttributeId = {Conversions.ToString(attributeSelector.AttributeId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#24 — line 3342
```sql
SELECT ShortDescription FROM OtherDescription od INNER JOIN [Option] opt ON od.DescriptionId = opt.DescriptionId WHERE od.LanguageId = {Conversions.ToString(Global.languageId)} AND opt.OptionId = {Conversions.ToString(optionSelector.OptionId)}
```

### HermanMiller.EOS.UI\TemplateContainer.cs#25 — line 3482
```sql
SELECT AttributeValue.AttributeValueId AS attr_val, AttributeValue.AttributeId AS attr_id FROM AttributeValue INNER JOIN ProductAttributeValues pav ON AttributeValue.AttributeValueId = pav.AttributeValueId INNER JOIN Attribute ON AttributeValue.AttributeId = Attribute.AttributeId WHERE pav.ProductId = {Conversions.ToString(productId)} AND (Attribute.AttributeType = 0 or Attribute.AttributeType = 2) ORDER BY Attribute.DisplayOrder
```

### HermanMiller.EOS.UI\TemplateContainer.cs#26 — line 3702
```sql
SELECT AttributeType FROM Attribute WHERE AttributeId = {Conversions.ToString(num)}
```

## ImportData.cs  (4)

### ImportData.cs#1 — line 601
```sql
INSERT INTO {text5} ({text2}) VALUES({text})
```

### ImportData.cs#2 — line 605
```sql
UPDATE {text5} SET {text2.Substring(text2.IndexOf(},{) + 1)} = {text.Substring(text.IndexOf(},{) + 1)} WHERE {text2.Substring(0, text2.IndexOf(},{))} = {text.Substring(0, text.IndexOf(},{))}
```

### ImportData.cs#3 — line 609
```sql
UPDATE {text5} SET {text2.Substring(text2.IndexOf(},{) + 1, text2.Substring(text2.IndexOf(},{) + 1).IndexOf(},{))} = {text.Substring(text.IndexOf(},{) + 1, text.Substring(text.IndexOf(},{) + 1).IndexOf(},{))}, {text2.Substring(text2.LastIndexOf(},{) + 1)} = {text.Substring(text.LastIndexOf(},{) + 1)} WHERE {text2.Substring(0, text2.IndexOf(},{))} = {text.Substring(0, text.IndexOf(},{))}
```

### ImportData.cs#4 — line 613
```sql
UPDATE {text5} SET {text2.Substring(text2.IndexOf(},{) + 1, text2.Substring(text2.IndexOf(},{) + 1).IndexOf(},{))} = {text.Substring(text.IndexOf(},{) + 1, text.Substring(text.IndexOf(},{) + 1).IndexOf(},{))} WHERE {text2.Substring(text2.LastIndexOf(},{) + 1)} = {text.Substring(text.LastIndexOf(},{) + 1)} AND {text2.Substring(0, text2.IndexOf(},{))} = {Conversions.ToString(int.Parse(text.Substring(0, text.IndexOf(},{))))}
```

## ItemEntry.cs  (17)

### ItemEntry.cs#1 — line 1145
```sql
SELECT Name, CatalogueId, LeadTime FROM Catalogue WHERE Status = 1 AND CatalogueId IN (
```

### ItemEntry.cs#2 — line 1229
```sql
SELECT SiteId, Description FROM Site WHERE SiteId NOT IN (20)
```

### ItemEntry.cs#3 — line 1251
```sql
SELECT Currency_ID, Currency, Description, Symbol FROM Currency
```

### ItemEntry.cs#4 — line 1300
```sql
SELECT DISTINCT Item FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId
```

### ItemEntry.cs#5 — line 1303
```sql
SELECT USItem AS Item FROM USItem INNER JOIN CatalogueProductCategories cpc ON USItem.ProductCategoryId = cpc.ProductCategoryId INNER JOIN ProductCategory pc ON USItem.ProductCategoryId = pc.ProductCategoryId WHERE cpc.Status = 1 AND pc.Status = 1 ORDER BY USItem{))}
```

### ItemEntry.cs#6 — line 1798
```sql
SELECT Product.ProductId, Product.Product, Product.ImageFile, Product.Name FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE Item = '{text2}' AND pr.ProductRangeId <> 999{) : (}SELECT USItem.USItemId AS ProductId, USItem.USItem AS Product, 'Images\Temp\na.jpg' AS ImageFile, USItem.Description AS Name FROM USItem WHERE USItem.USItem = '{text2}'{))}
```

### ItemEntry.cs#7 — line 1881
```sql
SELECT DISTINCT CASE WHEN od1.ShortDescription IS NULL THEN cpc.Name ELSE od1.ShortDescription END AS category_name, CASE WHEN od2.ShortDescription IS NULL THEN Catalogue.Name ELSE od2.ShortDescription END AS catalogue_name, pc.Product_Code FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {, _siteIdList[site_selector.SelectedIndex]),} {),}INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId {),}INNER JOIN CatalogueProductCategories cpc ON pr.ProductCategoryId = cpc.ProductCategoryId {),}INNER JOIN Catalogue ON cpc.CatalogueId = Catalogue.CatalogueId {),}LEFT OUTER JOIN OtherDescription od1 ON cpc.DescriptionId = od1.DescriptionId AND od1.LanguageId = {), Global.languageId),} {),}LEFT OUTER JOIN OtherDescription od2 ON Catalogue.DescriptionId = od2.DescriptionId AND od2.LanguageId = {), Global.languageId),} {),}WHERE Product.ProductId = {), num),} AND pr.ProductRangeId <> 999 AND cpc.CatalogueId = {), num8),} AND pc.SiteId = {), Global.SiteId(allowPLCOverride: true))) : (}SELECT 'US Catalogue' AS catalogue_name, cpc.Name AS category_name, USItem.Product_Code FROM USItem INNER JOIN CatalogueProductCategories cpc ON USItem.ProductCategoryId = cpc.ProductCategoryId WHERE USItem.USItemId = {Conversions.ToString(num)))}
```

### ItemEntry.cs#8 — line 1969
```sql
SELECT DISTINCT Catalogue.CatalogueId, Catalogue.LeadTime FROM Catalogue INNER JOIN CatalogueItems ci ON ci.CatalogueId = Catalogue.CatalogueId INNER JOIN Item ON ci.ItemId = Item.ItemId WHERE Item.Item = '{myitem}' ORDER BY Catalogue.LeadTime
```

### ItemEntry.cs#9 — line 1984
```sql
SELECT DISTINCT Catalogue.CatalogueId, Catalogue.LeadTime FROM Catalogue INNER JOIN CatalogueItems ci ON ci.CatalogueId = Catalogue.CatalogueId INNER JOIN ItemComponents itco ON ci.ItemId = itco.ItemId INNER JOIN Item ON itco.SubItemId = Item.ItemId WHERE Item.Item = '{myitem}' ORDER BY Catalogue.LeadTime
```

### ItemEntry.cs#10 — line 2006
```sql
SELECT DISTINCT Catalogue.CatalogueId, Catalogue.LeadTime FROM DealerCatalogues dc INNER JOIN Catalogue ON dc.CatalogueId = Catalogue.CatalogueId INNER JOIN CatalogueItems ci ON ci.CatalogueId = Catalogue.CatalogueId INNER JOIN Item ON ci.ItemId = Item.ItemId WHERE DealerNumId = {Conversions.ToString(mydealerNum)} AND Item.Item = '{myitem}' ORDER BY Catalogue.LeadTime
```

### ItemEntry.cs#11 — line 2047
```sql
SELECT Product FROM Product WHERE ProductRangeId IN (185)
```

### ItemEntry.cs#12 — line 2069
```sql
SELECT Item.ItemId FROM ItemComponents itco INNER JOIN Item ON itco.ItemId = Item.ItemId WHERE Item.Item = '{text2}'
```

### ItemEntry.cs#13 — line 2082
```sql
SELECT DISTINCT Catalogue.CatalogueId, Catalogue.LeadTime FROM Catalogue INNER JOIN CatalogueItems ci ON Catalogue.CatalogueId = ci.CatalogueId INNER JOIN Item ON ci.ItemId = Item.ItemId WHERE Item.Item = '{text2}' ORDER BY Catalogue.LeadTime
```

### ItemEntry.cs#14 — line 2135
```sql
SELECT ApplyUniqueOrderRules FROM Catalogue WHERE CatalogueId = {Conversions.ToString(mycatalogueId)}
```

### ItemEntry.cs#15 — line 2160
```sql
SELECT UniqueOrderFlag, Product FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId WHERE Item.Item = '{_itemSelections.BaseItem[num3].ToString()}'
```

### ItemEntry.cs#16 — line 2189
```sql
SELECT UniqueOrderFlag, Product FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId WHERE Item.Item = '{myitem}'
```

### ItemEntry.cs#17 — line 2511
```sql
SELECT Site.Site, Currency.Currency FROM Site INNER JOIN Currency ON Currency_ID = {Conversions.ToString(Global.currencyId)} WHERE SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}
```

## ItemPermutator.cs  (7)

### ItemPermutator.cs#1 — line 998
```sql
SELECT SiteId, Description FROM Site
```

### ItemPermutator.cs#2 — line 1042
```sql
SELECT DISTINCT cat.CatalogueId, cpc.ProductCategoryId, pr.ProductRangeId, cat.Name AS ctg_name, cpc.Name AS cat_name, pr.Name AS range_name FROM ProductRange pr INNER JOIN CatalogueProductCategories cpc ON pr.ProductCategoryId = cpc.ProductCategoryId INNER JOIN Catalogue cat ON cpc.CatalogueId = cat.CatalogueId WHERE ProductRangeId <> 999 AND ProductRangeId <> 1000 AND cat.Name NOT LIKE '%(Planning)%' AND cat.CatalogueId NOT IN (3, 5, 6, 7, 27, 28, 29) ORDER BY cat.CatalogueId, cpc.ProductCategoryId, pr.ProductRangeId
```

### ItemPermutator.cs#3 — line 1086
```sql
SELECT ProductCodeId, Product_Code, Description, BasePriceRef FROM Product_Code WHERE SiteId = {_siteIdList[SiteSelector.SelectedIndex].ToString()} ORDER BY Product_Code
```

### ItemPermutator.cs#4 — line 1393
```sql
INSERT INTO Item (/*ItemId,*/ ProductId, Item) VALUES (/*{Conversions.ToString(itemData.TempItemId)},*/ {Conversions.ToString(itemData.ProductId)}, '{itemData.Item}')
```

### ItemPermutator.cs#5 — line 1397
```sql
SELECT TOP 1 ItemId FROM Item ORDER BY ItemId DESC
```

### ItemPermutator.cs#6 — line 1406
```sql
UPDATE Product SET NewProduct = 0 WHERE ProductId = {Conversions.ToString(itemData.ProductId)}
```

### ItemPermutator.cs#7 — line 1426
```sql
INSERT INTO BaseAttributeValues (ItemId, AttributeValueId) VALUES ({Conversions.ToString(bAVData.ItemId)}, {Conversions.ToString(bAVData.AttributeValueId)})
```

## ItemValidator.cs  (1)

### ItemValidator.cs#1 — line 50
```sql
SELECT CatalogueId FROM DealerCatalogues WHERE DealerNumId = {Conversions.ToString(dealerNum)}
```

## LoadingThread.cs  (2)

### LoadingThread.cs#1 — line 34
```sql
SELECT Name FROM Catalogue WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### LoadingThread.cs#2 — line 42
```sql
SELECT Currency, Symbol FROM Currency WHERE Currency_ID = {Conversions.ToString(Global.currencyId)}
```

## Maintenance.cs  (82)

### Maintenance.cs#1 — line 20
```sql
SELECT LanguageId, ShortDescription FROM OtherDescription WHERE DescriptionId = {Conversions.ToString(descId)} AND LanguageId > 1
```

### Maintenance.cs#2 — line 30
```sql
UPDATE OtherDescription SET ShortDescription = N'{description.Replace(} {,}{).Replace(} {,}{).Trim()}' WHERE DescriptionId = {Conversions.ToString(descId)} AND LanguageId = {Conversions.ToString(Global.languageId)}
```

### Maintenance.cs#3 — line 35
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription ORDER BY DescriptionId DESC
```

### Maintenance.cs#4 — line 46
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num + 1)}, 1, N'{description}', '{origintable}')
```

### Maintenance.cs#5 — line 53
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num + 1)}, {text2.Substring(0, text2.IndexOf(}|{))}, N'{text2.Substring(text2.IndexOf(}|{) + 1)}', '{origintable}')
```

### Maintenance.cs#6 — line 57
```sql
UPDATE {origintable} SET DescriptionId = {Conversions.ToString(num + 1)} WHERE {origintable.Replace(}[{,}{).Replace(}]{,}{)}Id = {Conversions.ToString(originId)}
```

### Maintenance.cs#7 — line 91
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription ORDER BY DescriptionId DESC
```

### Maintenance.cs#8 — line 100
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num2)}, {Conversions.ToString(Global.languageId)}, '{catalogueName}', 'Catalogue')
```

### Maintenance.cs#9 — line 105
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num2)}, 1, '{catalogueName}', 'Catalogue')
```

### Maintenance.cs#10 — line 109
```sql
SELECT TOP 1 CatalogueId FROM Catalogue ORDER BY CatalogueId DESC
```

### Maintenance.cs#11 — line 119
```sql
SELECT CatalogueType, ImageFile FROM Catalogue WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#12 — line 149
```sql
INSERT INTO Catalogue (Name, LeadTime, DisplayOrder, DescriptionId, PrimarySiteId, CatalogueFlags, CatalogueType
```

### Maintenance.cs#13 — line 162
```sql
SELECT * FROM CatalogueProductCategories WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#14 — line 167
```sql
INSERT INTO CatalogueProductCategories (CatalogueId, ProductCategoryId, Name, DisplayOrder, ImageFile, Status, PSTemplateFile, ExtendedLeadTime,
```

### Maintenance.cs#15 — line 188
```sql
INSERT INTO CatalogueProductRanges SELECT {Conversions.ToString(num)} AS CatalogueId, ProductRangeId FROM CatalogueProductRanges WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#16 — line 191
```sql
INSERT INTO CatalogueAttributeValues SELECT {Conversions.ToString(num)} AS CatalogueId, AttributeValueId FROM CatalogueAttributeValues WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#17 — line 194
```sql
INSERT INTO CatalogueOptionValues SELECT {Conversions.ToString(num)} AS CatalogueId, OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#18 — line 197
```sql
INSERT INTO CatalogueItems SELECT {Conversions.ToString(num)} AS CatalogueId, ItemId FROM CatalogueItems WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#19 — line 200
```sql
INSERT INTO CatalogueItemsUnreleased SELECT {Conversions.ToString(num)} AS CatalogueId, ItemId FROM CatalogueItemsUnreleased WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#20 — line 203
```sql
INSERT INTO CatalogueItemExclusions SELECT {Conversions.ToString(num)} AS CatalogueId, ItemId FROM CatalogueItemExclusions WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#21 — line 206
```sql
INSERT INTO CatalogueItemOptionExclusions SELECT {Conversions.ToString(num)} AS CatalogueId, ItemId, OptionValueId FROM CatalogueItemOptionExclusions WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#22 — line 209
```sql
INSERT INTO CatalogueProductOptionExclusions SELECT {Conversions.ToString(num)} AS CatalogueId, ProductId, OptionValueId FROM CatalogueProductOptionExclusions WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#23 — line 212
```sql
INSERT INTO CatalogueApplicationText SELECT {Conversions.ToString(num)} AS CatalogueId, ProductId, LanguageId, ApplicationText FROM CatalogueApplicationText WHERE CatalogueId = {Conversions.ToString(clonedCatalogueId)}
```

### Maintenance.cs#24 — line 245
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription
```

### Maintenance.cs#25 — line 255
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num2)}, {Conversions.ToString(Global.languageId)}, '{categoryName}', 'CatalogueProductCategories')
```

### Maintenance.cs#26 — line 260
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num2)}, 1, '{categoryName}', 'CatalogueProductCategories')
```

### Maintenance.cs#27 — line 264
```sql
SELECT TOP 1 ProductCategoryId FROM ProductCategory WHERE ProductCategoryId <> 999 AND ProductCategoryId <> 1000
```

### Maintenance.cs#28 — line 273
```sql
SELECT TOP 1 DisplayOrder FROM CatalogueProductCategories WHERE CatalogueId = {Conversions.ToString(catalogueId)} ORDER BY DisplayOrder DESC
```

### Maintenance.cs#29 — line 282
```sql
INSERT INTO ProductCategory (/*ProductCategoryId,*/ Name, Status) VALUES (/*{Conversions.ToString(num)},*/ '{categoryName}', 0)
```

### Maintenance.cs#30 — line 285
```sql
INSERT INTO CatalogueProductCategories (CatalogueId, ProductCategoryId, Name, DisplayOrder, DescriptionId) VALUES ({Conversions.ToString(catalogueId)}, {Conversions.ToString(num)}, '{categoryName}', {Conversions.ToString(num3)}, {Conversions.ToString(num2)})
```

### Maintenance.cs#31 — line 319
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription
```

### Maintenance.cs#32 — line 329
```sql
SELECT TOP 1 ProductRangeId FROM ProductRange WHERE ProductRangeId <> 999 AND ProductRangeId <> 1000
```

### Maintenance.cs#33 — line 341
```sql
SELECT COUNT(*) AS cnt, pr.Name AS rng_name, pr.ProductCategoryId, pr.OrderCodeFormatString, pr.DisplayOrder, pr.DescriptionId, pr.Status FROM ProductRange pr GROUP BY pr.Name, pr.ProductCategoryId, pr.OrderCodeFormatString, pr.DisplayOrder, pr.DescriptionId, pr.Status HAVING pr.ProductCategoryId = {Conversions.ToString(clonedCategoryId)} AND pr.Status > -1 ORDER BY DisplayOrder
```

### Maintenance.cs#34 — line 357
```sql
INSERT INTO ProductRange (ProductCategoryId, Name, OrderCodeFormatString, DisplayOrder, DescriptionId) VALUES ({Conversions.ToString(categoryId)}, '{text2}', '{sqlDataReader[}OrderCodeFormatString{].ToString()}', {sqlDataReader[}DisplayOrder{].ToString()}, {Conversions.ToString(num2)})
```

### Maintenance.cs#35 — line 359
```sql
INSERT INTO CatalogueProductRanges (CatalogueId, ProductRangeId) VALUES ({Conversions.ToString(catalogueId)}, {Conversions.ToString(num)}){)}
```

### Maintenance.cs#36 — line 374
```sql
INSERT INTO CatalogueProductRanges{))
 {
 int num5 = int.Parse(text.Substring(text.IndexOf(}VALUES ({) + 8).Substring(0, text.Substring(text.IndexOf(}VALUES ({) + 8).IndexOf(}, {)))}
```

### Maintenance.cs#37 — line 378
```sql
SELECT ProductRangeId FROM CatalogueProductRanges WHERE CatalogueId = {Conversions.ToString(num5)} AND ProductRangeId = {Conversions.ToString(num6)}
```

### Maintenance.cs#38 — line 396
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({arrayList2[j].ToString()}, {Conversions.ToString(Global.languageId)}, '{arrayList3[j].ToString()}', 'ProductRange')
```

### Maintenance.cs#39 — line 401
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({arrayList2[j].ToString()}, 1, '{arrayList3[j].ToString()}', 'ProductRange')
```

### Maintenance.cs#40 — line 409
```sql
INSERT INTO ProductRange (ProductCategoryId, Name, OrderCodeFormatString, DisplayOrder, DescriptionId) VALUES ({Conversions.ToString(categoryId)}, '{rangeName}', NULL, 1, {Conversions.ToString(num2)})
```

### Maintenance.cs#41 — line 412
```sql
INSERT INTO CatalogueProductRanges (CatalogueId, ProductRangeId) VALUES ({Conversions.ToString(catalogueId)}, {Conversions.ToString(num)})
```

### Maintenance.cs#42 — line 415
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num2)}, {Conversions.ToString(Global.languageId)}, '{rangeName}', 'ProductRange')
```

### Maintenance.cs#43 — line 420
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num2)}, 1, '{rangeName}', 'ProductRange')
```

### Maintenance.cs#44 — line 489
```sql
SELECT PSTemplateFile, ImageFile FROM CatalogueProductCategories cpc WHERE cpc.CatalogueId = {Conversions.ToString(catalogueId)} AND cpc.ProductCategoryId = {Conversions.ToString(clonedCategoryId)}
```

### Maintenance.cs#45 — line 496
```sql
UPDATE CatalogueProductCategories SET PSTemplateFile = '{parseTemplateXMLFileName(}temp_{categoryName}Template_{Conversions.ToString(num)}.xml{)}', ImageFile = '{sqlDataReader[}ImageFile{].ToString()}' WHERE CatalogueId = {Conversions.ToString(catalogueId)} AND ProductCategoryId = {Conversions.ToString(num))}
```

### Maintenance.cs#46 — line 509
```sql
SELECT TOP 1 AttributeId FROM Attribute
```

### Maintenance.cs#47 — line 520
```sql
SELECT AttributeId, Name, AttributeType, OrderCodeFormatKey, DisplayOrder, DescriptionId FROM Attribute WHERE ProductCategoryId = {Conversions.ToString(clonedCategoryId)}
```

### Maintenance.cs#48 — line 527
```sql
INSERT INTO Attribute (/*AttributeId,*/ ProductCategoryId, Name, AttributeType,
```

### Maintenance.cs#49 — line 555
```sql
SELECT TOP 1 AttributeValueId FROM AttributeValue
```

### Maintenance.cs#50 — line 566
```sql
SELECT AttributeValueId, Name, OrderCodeValue, DisplayOrdinal, ImageFile, ParentAttributeValueId, DescriptionId, Status FROM AttributeValue WHERE AttributeId = {arrayList[j].ToString()} AND Status > -1
```

### Maintenance.cs#51 — line 571
```sql
INSERT INTO AttributeValue (/*AttributeValueId,*/ AttributeId, Name,
```

### Maintenance.cs#52 — line 616
```sql
SELECT TOP 1 OptionId FROM [Option]
```

### Maintenance.cs#53 — line 627
```sql
SELECT OptionId, Name, OrderCodeFormatKey, DisplayOrder, DescriptionId FROM [Option] WHERE ProductCategoryId = {Conversions.ToString(clonedCategoryId)}
```

### Maintenance.cs#54 — line 634
```sql
INSERT INTO [Option] (/*OptionId,*/ ProductCategoryId, Name,
```

### Maintenance.cs#55 — line 662
```sql
SELECT TOP 1 OptionValueId FROM OptionValue
```

### Maintenance.cs#56 — line 673
```sql
SELECT OptionValueId, Name, OrderCodeValue, CADSuffix, DisplayOrdinal, ImageFile, CADMaterial, DescriptionId, Status FROM OptionValue WHERE OptionId = {arrayList2[j].ToString()} AND Status > -1
```

### Maintenance.cs#57 — line 678
```sql
INSERT INTO OptionValue (/*OptionValueId,*/ OptionId, Name,
```

### Maintenance.cs#58 — line 735
```sql
INSERT INTO CatalogueAttributeValues (CatalogueId, AttributeValueId) VALUES ({Conversions.ToString(catalogueId)}, {arrayList6[i].ToString()})
```

### Maintenance.cs#59 — line 742
```sql
INSERT INTO CatalogueOptionValues (CatalogueId, OptionValueId) VALUES ({Conversions.ToString(catalogueId)}, {arrayList7[i].ToString()})
```

### Maintenance.cs#60 — line 782
```sql
SELECT TOP 1 DescriptionId FROM ProductDescription
```

### Maintenance.cs#61 — line 792
```sql
INSERT INTO ProductDescription (DescriptionId, LanguageId, ShortDescription, LongDescription) VALUES ({Conversions.ToString(num2)}, 1, '{text2}', '{text2}')
```

### Maintenance.cs#62 — line 795
```sql
SELECT TOP 1 ProductId FROM Product
```

### Maintenance.cs#63 — line 806
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### Maintenance.cs#64 — line 809
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### Maintenance.cs#65 — line 818
```sql
INSERT INTO PDMAudit.dbo.ProductUpdates (TransactionId, ProductId, NewProduct) VALUES ({Conversions.ToString(num3)}, {Conversions.ToString(num)}, '{product}')
```

### Maintenance.cs#66 — line 821
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### Maintenance.cs#67 — line 824
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### Maintenance.cs#68 — line 833
```sql
INSERT INTO PDMAudit.dbo.ProductOCFS (TransactionId, ProductId, PrevOCFS, NewOCFS) VALUES ({Conversions.ToString(num3)}, {Conversions.ToString(num)}, '', 'initialRangeId = {Conversions.ToString(prodRangeId)}')
```

### Maintenance.cs#69 — line 844
```sql
INSERT INTO Product (ProductRangeId, Name, Product, DisplayOrder, ProductCodeId, DescriptionId, NewProduct, ImageFile, CADAlias
```

### Maintenance.cs#70 — line 860
```sql
INSERT INTO ProductAttributeValues (ProductId, AttributeValueId) VALUES ({Conversions.ToString(num)}, {funcAttrs[i].ToString()})
```

### Maintenance.cs#71 — line 863
```sql
SELECT COUNT(*) AS cnt FROM CatalogueAttributeValues WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND AttributeValueId = {funcAttrs[i].ToString()}
```

### Maintenance.cs#72 — line 874
```sql
INSERT INTO CatalogueAttributeValues (CatalogueId, AttributeValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {funcAttrs[i].ToString()})
```

### Maintenance.cs#73 — line 908
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription
```

### Maintenance.cs#74 — line 918
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num)}, {Conversions.ToString(Global.languageId)}, '{description}', 'Attribute')
```

### Maintenance.cs#75 — line 923
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num)}, 1, '{description}', 'Attribute')
```

### Maintenance.cs#76 — line 927
```sql
SELECT TOP 1 AttributeId FROM Attribute
```

### Maintenance.cs#77 — line 936
```sql
INSERT INTO Attribute (ProductCategoryId, Name,
```

### Maintenance.cs#78 — line 975
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription
```

### Maintenance.cs#79 — line 985
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num)}, {Conversions.ToString(Global.languageId)}, '{description}', '[Option]')
```

### Maintenance.cs#80 — line 990
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num)}, 1, '{description}', '[Option]')
```

### Maintenance.cs#81 — line 994
```sql
SELECT TOP 1 OptionId FROM [Option]
```

### Maintenance.cs#82 — line 1003
```sql
INSERT INTO [Option] (ProductCategoryId, Name,
```

## OrderCategories.cs  (2)

### OrderCategories.cs#1 — line 108
```sql
SELECT cpc.ProductCategoryId, cpc.DisplayOrder, CASE WHEN od.ShortDescription IS NULL THEN cpc.Name ELSE od.ShortDescription END AS ShortDescription FROM CatalogueProductCategories cpc LEFT OUTER JOIN OtherDescription od ON cpc.DescriptionId = od.DescriptionId AND od.LanguageId = {Conversions.ToString(Global.languageId)} WHERE cpc.CatalogueId = {Conversions.ToString(Global.catalogueId)}ORDER BY cpc.DisplayOrder
```

### OrderCategories.cs#2 — line 178
```sql
UPDATE CatalogueProductCategories SET DisplayOrder = {textBox.Text.ToString()} WHERE ProductCategoryId = {textBox.Tag.ToString()} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

## ParameterSelection.cs  (4)

### ParameterSelection.cs#1 — line 349
```sql
SELECT Catalogue.Name, Catalogue.CatalogueId, puc.ReadOnly FROM PDMUserCatalogues puc INNER JOIN Catalogue ON puc.CatalogueId = Catalogue.CatalogueId WHERE puc.UserId = {Conversions.ToString(AuthenticateUser.UserId)} AND Catalogue.Status = 1
```

### ParameterSelection.cs#2 — line 384
```sql
SELECT SiteId, Description FROM Site
```

### ParameterSelection.cs#3 — line 405
```sql
SELECT Language_ID, Language FROM Language
```

### ParameterSelection.cs#4 — line 426
```sql
SELECT Currency_ID, Description FROM Currency
```

## ParseOrderCode.cs  (1)

### ParseOrderCode.cs#1 — line 22
```sql
SELECT USAdditionalOptionValueId FROM USDependentOptionValues WHERE USOptionValueId = {Conversions.ToString(USoptvalid)}
```

## PermutateThread.cs  (5)

### PermutateThread.cs#1 — line 68
```sql
SELECT TOP 1 ItemId FROM Item ORDER BY ItemId DESC
```

### PermutateThread.cs#2 — line 88
```sql
SELECT DISTINCT Product.ProductId, Product.Product, attr.DisplayOrder, attr.AttributeType, atval.AttributeValueId, atval.DisplayOrdinal, atval.OrderCodeValue FROM Product INNER JOIN /*root*/Product_Code ON Product.ProductCodeId = Product_Code.ProductCodeId INNER JOIN ProductAttributeValues pav ON Product.ProductId = pav.ProductId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId
```

### PermutateThread.cs#3 — line 136
```sql
SELECT AttributeValueId, ExcludedAttributeValueId FROM AttributeValueExclusions ORDER BY ExcludedAttributeValueId, AttributeValueId
```

### PermutateThread.cs#4 — line 161
```sql
SELECT DISTINCT attr.AttributeId, attr.DisplayOrder, atval.AttributeValueId, atval.DisplayOrdinal, atval.OrderCodeValue FROM Product INNER JOIN /*root*/Product_Code ON Product.ProductCodeId = Product_Code.ProductCodeId INNER JOIN ProductAttributeValues pav ON Product.ProductId = pav.ProductId INNER JOIN CatalogueAttributeValues cav ON pav.AttributeValueId = cav.AttributeValueId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE atval.OrderCodeValue IS NOT NULL
```

### PermutateThread.cs#5 — line 272
```sql
SELECT COUNT(*) AS cnt FROM Item WHERE Item = '{text5}'
```

## ProductCategories.cs  (80)

### ProductCategories.cs#1 — line 424
```sql
SELECT CASE WHEN od.ShortDescription IS NULL THEN DPSText.Description ELSE od.ShortDescription END AS ShortDescription FROM DPSText LEFT OUTER JOIN OtherDescription od ON DPSText.DescriptionId = od.DescriptionId AND od.LanguageId = {Conversions.ToString(Global.languageId)} WHERE DPSText.DPSTextId = 5
```

### ProductCategories.cs#2 — line 437
```sql
SELECT CASE WHEN od.ShortDescription IS NULL THEN DPSText.Description ELSE od.ShortDescription END AS ShortDescription FROM DPSText LEFT OUTER JOIN OtherDescription od ON DPSText.DescriptionId = od.DescriptionId AND od.LanguageId = {Conversions.ToString(Global.languageId)} WHERE DPSText.DPSTextId = 4
```

### ProductCategories.cs#3 — line 450
```sql
SELECT CASE WHEN od.ShortDescription IS NULL THEN DPSText.Description ELSE od.ShortDescription END AS ShortDescription FROM DPSText LEFT OUTER JOIN OtherDescription od ON DPSText.DescriptionId = od.DescriptionId AND od.LanguageId = {Conversions.ToString(Global.languageId)} WHERE DPSText.DPSTextId = 28
```

### ProductCategories.cs#4 — line 463
```sql
SELECT CASE WHEN od.ShortDescription IS NULL THEN DPSText.Description ELSE od.ShortDescription END AS ShortDescription FROM DPSText LEFT OUTER JOIN OtherDescription od ON DPSText.DescriptionId = od.DescriptionId AND od.LanguageId = {Conversions.ToString(Global.languageId)} WHERE DPSText.DPSTextId = 29
```

### ProductCategories.cs#5 — line 476
```sql
SELECT CASE WHEN od.ShortDescription IS NULL THEN DPSText.Description ELSE od.ShortDescription END AS ShortDescription FROM DPSText LEFT OUTER JOIN OtherDescription od ON DPSText.DescriptionId = od.DescriptionId AND od.LanguageId = {Conversions.ToString(Global.languageId)} WHERE DPSText.DPSTextId = 2
```

### ProductCategories.cs#6 — line 490
```sql
SELECT CASE WHEN od.ShortDescription IS NULL THEN DPSText.Description ELSE od.ShortDescription END AS ShortDescription FROM DPSText LEFT OUTER JOIN OtherDescription od ON DPSText.DescriptionId = od.DescriptionId AND od.LanguageId = {Conversions.ToString(Global.languageId)} WHERE DPSText.DPSTextId = 3
```

### ProductCategories.cs#7 — line 535
```sql
SELECT Name, CatalogueId FROM Catalogue WHERE Status = 1 AND CatalogueId IN (
```

### ProductCategories.cs#8 — line 573
```sql
SELECT od.ShortDescription FROM OtherDescription od INNER JOIN Catalogue ON od.DescriptionId = Catalogue.DescriptionId WHERE CatalogueId = {_catalogueIdList[i].ToString()} AND LanguageId = {Conversions.ToString(Global.languageId)}
```

### ProductCategories.cs#9 — line 598
```sql
SELECT COUNT(*) AS cnt FROM CatalogueProductCategories WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#10 — line 678
```sql
SELECT LeadTime FROM Catalogue WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#11 — line 701
```sql
SELECT ImageFile, ExtendedLeadTime FROM CatalogueProductCategories WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductCategoryId = {imageButton.Tag.ToString()}
```

### ProductCategories.cs#12 — line 768
```sql
SELECT Language FROM Language WHERE Language_Id = {Conversions.ToString(Global.languageId)}
```

### ProductCategories.cs#13 — line 777
```sql
SELECT LanguageId FROM CatalogueTranslations WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#14 — line 815
```sql
SELECT USCategory FROM ProductCategory WHERE ProductCategoryId = {Conversions.ToString(mycatId)}
```

### ProductCategories.cs#15 — line 830
```sql
SELECT COUNT(*) AS cnt FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId INNER JOIN ProductCategory pc ON pr.ProductCategoryId = pc.ProductCategoryId WHERE pc.ProductCategoryId = {Conversions.ToString(mycatId)}
```

### ProductCategories.cs#16 — line 1002
```sql
UPDATE CatalogueProductCategories SET PSTemplateFile = '{releaseTemplate}' WHERE PSTemplateFile = '{templateXML}'
```

### ProductCategories.cs#17 — line 1135
```sql
SELECT Name, DisplayOrder, ImageFile, PSTemplateFile, HBTemplateFile, DescriptionId FROM CatalogueProductCategories WHERE ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#18 — line 1141
```sql
INSERT INTO CatalogueProductCategories (CatalogueId, ProductCategoryId, Name, DisplayOrder, ExtendedLeadTime, Status,
```

### ProductCategories.cs#19 — line 1175
```sql
SELECT cpr.ProductRangeId FROM CatalogueProductRanges cpr INNER JOIN ProductRange pr ON cpr.ProductRangeId = pr.ProductRangeId WHERE cpr.CatalogueId = {Conversions.ToString(num2)} AND pr.ProductCategoryId = {Conversions.ToString(num)) : (}SELECT ProductRangeId FROM ProductRange WHERE ProductCategoryId = {Conversions.ToString(num)))}
```

### ProductCategories.cs#20 — line 1180
```sql
INSERT INTO CatalogueProductRanges (CatalogueId, ProductRangeId) VALUES ({Conversions.ToString(Global.catalogueId)}, {sqlDataReader[}ProductRangeId{].ToString()}){)}
```

### ProductCategories.cs#21 — line 1183
```sql
SELECT cav.AttributeValueId FROM CatalogueAttributeValues cav INNER JOIN AttributeValue atval ON cav.AttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE cav.CatalogueId = {Conversions.ToString(num2)} AND attr.ProductCategoryId = {Conversions.ToString(num)} AND atval.AttributeValueId NOT IN (SELECT AttributeValueId FROM CatalogueAttributeValues WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} UNION SELECT -1){) : (}SELECT AttributeValueId FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE attr.ProductCategoryId = {Conversions.ToString(num)))}
```

### ProductCategories.cs#22 — line 1188
```sql
INSERT INTO CatalogueAttributeValues (CatalogueId, AttributeValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {sqlDataReader[}AttributeValueId{].ToString()}){)}
```

### ProductCategories.cs#23 — line 1191
```sql
SELECT cov.OptionValueId FROM CatalogueOptionValues cov INNER JOIN OptionValue optval ON cov.OptionValueId = optval.OptionValueId INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE cov.CatalogueId = {Conversions.ToString(num2)} AND opt.ProductCategoryId = {Conversions.ToString(num)} AND optval.OptionValueId NOT IN (SELECT OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} UNION SELECT -1){) : (}SELECT OptionValueId FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.ProductCategoryId = {Conversions.ToString(num)))}
```

### ProductCategories.cs#24 — line 1196
```sql
INSERT INTO CatalogueOptionValues (CatalogueId, OptionValueId) VALUES ({Conversions.ToString(Global.catalogueId)}, {sqlDataReader[}OptionValueId{].ToString()}){)}
```

### ProductCategories.cs#25 — line 1244
```sql
UPDATE Catalogue SET IsWebCatalogue = {Conversions.ToString(num)} WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#26 — line 1266
```sql
UPDATE Catalogue SET LeadTimeDisplay = {Conversions.ToString(num)} WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#27 — line 1283
```sql
SELECT LeadTime FROM Catalogue WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#28 — line 1303
```sql
UPDATE Catalogue SET LeadTime = {Conversions.ToString(num)} WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#29 — line 1364
```sql
SELECT COUNT(*) AS cnt FROM CatalogueProductCategories WHERE ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#30 — line 1381
```sql
SELECT pc.Name, pc.Status, cpc.Status AS cpc_status FROM ProductCategory pc INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId WHERE cpc.CatalogueId = {Conversions.ToString(Global.catalogueId)} AND pc.ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#31 — line 1398
```sql
UPDATE ProductCategory SET Status = 1 WHERE ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#32 — line 1403
```sql
UPDATE CatalogueProductCategories SET Status = 1 WHERE ProductCategoryId = {Conversions.ToString(num)} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#33 — line 1410
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### ProductCategories.cs#34 — line 1413
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### ProductCategories.cs#35 — line 1422
```sql
INSERT INTO PDMAudit.dbo.CPCUpdates (TransactionId, CatalogueId, ProductCategoryId, Description, Status, PrevStatus, GlobalStatus, PrevGlobalStatus, ActionTaken) VALUES ({Conversions.ToString(num7)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(num)}, '{text5}', {Conversions.ToString(num5)}, {Conversions.ToString(num3)}, {Conversions.ToString(num6)}, {Conversions.ToString(num4)}, 'ACT')
```

### ProductCategories.cs#36 — line 1446
```sql
SELECT COUNT(*) AS cnt FROM CatalogueProductCategories WHERE ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#37 — line 1463
```sql
SELECT pc.Name, pc.Status, cpc.Status AS cpc_status FROM ProductCategory pc INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId WHERE cpc.CatalogueId = {Conversions.ToString(Global.catalogueId)} AND pc.ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#38 — line 1480
```sql
UPDATE ProductCategory SET Status = 0 WHERE ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#39 — line 1485
```sql
UPDATE CatalogueProductCategories SET Status = 0 WHERE ProductCategoryId = {Conversions.ToString(num)} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#40 — line 1492
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### ProductCategories.cs#41 — line 1495
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### ProductCategories.cs#42 — line 1504
```sql
INSERT INTO PDMAudit.dbo.CPCUpdates (TransactionId, CatalogueId, ProductCategoryId, Description, Status, PrevStatus, GlobalStatus, PrevGlobalStatus, ActionTaken) VALUES ({Conversions.ToString(num13)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(num)}, '{text6}', {Conversions.ToString(num11)}, {Conversions.ToString(num9)}, {Conversions.ToString(num12)}, {Conversions.ToString(num10)}, 'URL')
```

### ProductCategories.cs#43 — line 1528
```sql
SELECT COUNT(*) AS cnt FROM CatalogueProductCategories WHERE ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#44 — line 1545
```sql
SELECT pc.Name, pc.Status, cpc.Status AS cpc_status FROM ProductCategory pc INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId WHERE cpc.CatalogueId = {Conversions.ToString(Global.catalogueId)} AND pc.ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#45 — line 1562
```sql
UPDATE ProductCategory SET Status = 2 WHERE ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#46 — line 1567
```sql
UPDATE CatalogueProductCategories SET Status = 2 WHERE ProductCategoryId = {Conversions.ToString(num)} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#47 — line 1574
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### ProductCategories.cs#48 — line 1577
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### ProductCategories.cs#49 — line 1586
```sql
INSERT INTO PDMAudit.dbo.CPCUpdates (TransactionId, CatalogueId, ProductCategoryId, Description, Status, PrevStatus, GlobalStatus, PrevGlobalStatus, ActionTaken) VALUES ({Conversions.ToString(num19)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(num)}, '{text7}', {Conversions.ToString(num17)}, {Conversions.ToString(num15)}, {Conversions.ToString(num18)}, {Conversions.ToString(num16)}, 'OBS')
```

### ProductCategories.cs#50 — line 1610
```sql
SELECT COUNT(*) AS cnt FROM CatalogueProductCategories WHERE ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#51 — line 1627
```sql
SELECT pc.Name, pc.Status, cpc.Status AS cpc_status FROM ProductCategory pc INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId WHERE cpc.CatalogueId = {Conversions.ToString(Global.catalogueId)} AND pc.ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#52 — line 1644
```sql
UPDATE ProductCategory SET Status = 3 WHERE ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#53 — line 1649
```sql
UPDATE CatalogueProductCategories SET Status = 3 WHERE ProductCategoryId = {Conversions.ToString(num)} AND CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#54 — line 1656
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### ProductCategories.cs#55 — line 1659
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### ProductCategories.cs#56 — line 1668
```sql
INSERT INTO PDMAudit.dbo.CPCUpdates (TransactionId, CatalogueId, ProductCategoryId, Description, Status, PrevStatus, GlobalStatus, PrevGlobalStatus, ActionTaken) VALUES ({Conversions.ToString(num25)}, {Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(num)}, '{text8}', {Conversions.ToString(num23)}, {Conversions.ToString(num21)}, {Conversions.ToString(num24)}, {Conversions.ToString(num22)}, 'HLD')
```

### ProductCategories.cs#57 — line 1683
```sql
SELECT ImageFile FROM CatalogueProductCategories WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#58 — line 1696
```sql
UPDATE CatalogueProductCategories SET ImageFile = 'Images\Products\{openFileDialog.FileName.Substring(openFileDialog.FileName.LastIndexOf(}\{) + 1)}' WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#59 — line 1750
```sql
SELECT DISTINCT ProductCategory.ProductCategoryId, ProductCategory.Name + ' (' + SUBSTRING(REPLACE(PSTemplateFile, 'temp_', ''), 1, PATINDEX('%[A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z]%', SUBSTRING(REPLACE(PSTemplateFile, 'temp_', ''), 2, 99) COLLATE SQL_Latin1_General_CP1_CS_AS)) + ')' AS short_desc, cpc.DisplayOrder, cpc.ImageFile, cpc.PSTemplateFile, (CASE WHEN PSTemplateFile IS NULL THEN 0 WHEN ProductCategory.Status <> 1 THEN 2 ELSE 1 END) AS 'BackColour', 1 AS 'Available' FROM ProductCategory INNER JOIN CatalogueProductCategories cpc ON ProductCategory.ProductCategoryId = cpc.ProductCategoryId WHERE ProductCategory.ProductCategoryId NOT IN (1, 127, 128, 129, 999, 1000
```

### ProductCategories.cs#60 — line 1804
```sql
SELECT DISTINCT cpc.CatalogueId, convert(int, convert(varchar, cpc.CatalogueId) + '' + convert(varchar, ProductCategory.ProductCategoryId)) AS ProductCategoryId, ProductCategory.Name + ' (' + Catalogue.Name + ')|' + convert(varchar, cpc.CatalogueId) AS short_desc, cpc.DisplayOrder, cpc.ImageFile, cpc.PSTemplateFile, (CASE WHEN PSTemplateFile IS NULL THEN 0 WHEN ProductCategory.Status <> 1 THEN 2 ELSE 1 END) AS 'BackColour', 1 AS 'Available' FROM ProductCategory INNER JOIN CatalogueProductCategories cpc ON ProductCategory.ProductCategoryId = cpc.ProductCategoryId INNER JOIN Catalogue ON cpc.CatalogueId = Catalogue.CatalogueId WHERE Catalogue.LeadTimeDisplay = 1 AND ProductCategory.ProductCategoryId NOT IN (-1,
```

### ProductCategories.cs#61 — line 1844
```sql
DELETE FROM CatalogueProductCategories WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductCategoryId = {Conversions.ToString(num)}
```

### ProductCategories.cs#62 — line 1847
```sql
DELETE FROM CatalogueProductRanges WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ProductRangeId IN (SELECT ProductRangeId FROM ProductRange WHERE ProductCategoryId = {Conversions.ToString(num)})
```

### ProductCategories.cs#63 — line 1850
```sql
DELETE FROM CatalogueAttributeValues WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND AttributeValueId IN (SELECT AttributeValueId FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE attr.ProductCategoryId = {Conversions.ToString(num)})
```

### ProductCategories.cs#64 — line 1853
```sql
DELETE FROM CatalogueOptionValues WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND OptionValueId IN (SELECT OptionValueId FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.ProductCategoryId = {Conversions.ToString(num)})
```

### ProductCategories.cs#65 — line 1949
```sql
SELECT Name FROM Catalogue WHERE Name = '{text4}'
```

### ProductCategories.cs#66 — line 1985
```sql
INSERT INTO DealerCatalogues (DealerNumId, CatalogueId) VALUES (1, {Conversions.ToString(num27)})
```

### ProductCategories.cs#67 — line 1990
```sql
INSERT INTO DealerCatalogues (DealerNumId, CatalogueId) VALUES ({Conversions.ToString(AuthenticateUser.DefaultDealerNum)}, {Conversions.ToString(num27)})
```

### ProductCategories.cs#68 — line 2007
```sql
SELECT UserId FROM PDMUserPrivileges WHERE UserName = '{Environment.UserName.ToUpper()}'
```

### ProductCategories.cs#69 — line 2041
```sql
SELECT UserId, FullName FROM PDMUserPrivileges WHERE UserName <> '{Environment.UserName.ToUpper()}' AND FullName IS NOT NULL AND SkypeName <> 'OBS' ORDER BY FullName
```

### ProductCategories.cs#70 — line 2065
```sql
INSERT INTO PDMUserCatalogues (UserId, CatalogueId, ReadOnly) VALUES ({arrayList2[num32].ToString()}, {Conversions.ToString(num27)}, 0)
```

### ProductCategories.cs#71 — line 2070
```sql
SELECT COUNT(*) AS cnt FROM PDMUserCatalogues WHERE UserId = {arrayList2[num32].ToString()} AND ReadOnly = 0
```

### ProductCategories.cs#72 — line 2078
```sql
INSERT INTO PDMUserCatalogues (UserId, CatalogueId, ReadOnly) VALUES ({arrayList2[num32].ToString()}, {Conversions.ToString(num27)}, 1){) : (}INSERT INTO PDMUserCatalogues (UserId, CatalogueId, ReadOnly) VALUES ({arrayList2[num32].ToString()}, {Conversions.ToString(num27)}, 0){))}
```

### ProductCategories.cs#73 — line 2084
```sql
select userid from PDMUserPrivileges where UserName <> '{Environment.UserName.ToUpper()}' and pdmadministrator=0 and pdmtester=1
```

### ProductCategories.cs#74 — line 2098
```sql
INSERT INTO PDMUserCatalogues (UserId, CatalogueId, ReadOnly) VALUES ({arrayList3[num35].ToString()}, {Conversions.ToString(num27)}, 1)
```

### ProductCategories.cs#75 — line 2103
```sql
select userid from PDMUserPrivileges where UserName <> '{Environment.UserName.ToUpper()}' and pdmadministrator=1
```

### ProductCategories.cs#76 — line 2117
```sql
INSERT INTO PDMUserCatalogues (UserId, CatalogueId, ReadOnly) VALUES ({arrayList4[num37].ToString()}, {Conversions.ToString(num27)}, 0)
```

### ProductCategories.cs#77 — line 2159
```sql
SELECT pc.Name, pc.Status, cpc.Status AS ctg_status FROM ProductCategory pc INNER JOIN CatalogueProductCategories cpc ON pc.ProductCategoryId = cpc.ProductCategoryId WHERE pc.ProductCategoryId = {Conversions.ToString(num2)} AND cpc.CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#78 — line 2172
```sql
SELECT Name, IsWebCatalogue, LeadTimeDisplay FROM Catalogue WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductCategories.cs#79 — line 2322
```sql
SELECT Name, LeadTime FROM Catalogue WHERE CatalogueId = {Conversions.ToString(int.Parse(_catalogueIdList[CatalogueSelector.SelectedIndex].ToString()))}
```

### ProductCategories.cs#80 — line 2331
```sql
SELECT od.ShortDescription FROM OtherDescription od INNER JOIN Catalogue ON od.DescriptionId = Catalogue.DescriptionId WHERE CatalogueId = {Conversions.ToString(int.Parse(_catalogueIdList[CatalogueSelector.SelectedIndex].ToString()))} AND LanguageId = {Conversions.ToString(Global.languageId)}
```

## ProductIntroduction.cs  (10)

### ProductIntroduction.cs#1 — line 900
```sql
SELECT DISTINCT pc.ProductCodeId, pc.Product_Code + ' | ' + pc.Description AS Product_Code FROM Product_Code pc WHERE pc.SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} ORDER BY Product_Code
```

### ProductIntroduction.cs#2 — line 1195
```sql
SELECT ProductRangeId, Name FROM ProductRange WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND Status > -1 AND Status < 2 ORDER BY DisplayOrder
```

### ProductIntroduction.cs#3 — line 1280
```sql
SELECT attr.AttributeId, attr.Name AS attr_name, atval.AttributeValueId, atval.Name AS atval_name FROM Attribute attr LEFT OUTER JOIN AttributeValue atval ON attr.AttributeId = atval.AttributeId AND atval.Status > -1 AND atval.Status < 2 WHERE attr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND (attr.OrderCodeFormatKey IS NULL OR attr.AttributeType = 0) AND attr.AttributeType <> 2
```

### ProductIntroduction.cs#4 — line 1424
```sql
SELECT DISTINCT Product, pr.ProductRangeId, pr.Name AS pr_name, atval.AttributeValueId, atval.Name AS atval_name, attr.DisplayOrder, atval.DisplayOrdinal FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId INNER JOIN ProductAttributeValues pav ON Product.ProductId = pav.ProductId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} And attr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} And attr.OrderCodeFormatKey Is NULL And attr.AttributeType <> 2 ORDER BY Product, attr.DisplayOrder, atval.DisplayOrdinal
```

### ProductIntroduction.cs#5 — line 1649
```sql
SELECT TOP 1 DescriptionId FROM OtherDescription
```

### ProductIntroduction.cs#6 — line 1659
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num)}, {Conversions.ToString(Global.languageId)}, '{text4}', 'AttributeValue')
```

### ProductIntroduction.cs#7 — line 1664
```sql
INSERT INTO OtherDescription (DescriptionId, LanguageId, ShortDescription, RelatedTable) VALUES ({Conversions.ToString(num)}, 1, '{text4}', 'AttributeValue')
```

### ProductIntroduction.cs#8 — line 1670
```sql
INSERT INTO AttributeValue (AttributeId, Name, DescriptionId) VALUES ({Conversions.ToString(num2)}, 'newvalue', {Conversions.ToString(num)})
```

### ProductIntroduction.cs#9 — line 1681
```sql
SELECT Name, OrderCodeFormatKey, DisplayOrder FROM Attribute WHERE AttributeId = {Conversions.ToString(_parentId)}
```

### ProductIntroduction.cs#10 — line 1863
```sql
SELECT Product FROM Product WHERE Product = '{product}'
```

## ProductMaintenance.cs  (36)

### ProductMaintenance.cs#1 — line 636
```sql
SELECT ProductRangeId FROM ProductRange WHERE Name = '{rangename}' AND ProductCategoryId IN (SELECT ProductCategoryId FROM ProductCategory WHERE Name = '{text2}')
```

### ProductMaintenance.cs#2 — line 672
```sql
SELECT ProductCodeId FROM Product_Code WHERE Product_Code = '{productcodedesc.Substring(0, productcodedesc.IndexOf(}|{)).Trim(' ')}' AND Description = '{productcodedesc.Substring(checked(productcodedesc.IndexOf(}|{) + 1)).Trim(' ')}' AND SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}
```

### ProductMaintenance.cs#3 — line 724
```sql
SELECT DISTINCT Product.Product, pav.AttributeValueId AS pav_atvalId, mpv.AttributeValueId AS mpv_atvalId FROM Product INNER JOIN ProductAttributeValues pav On Product.ProductId = pav.ProductId INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId And attr.AttributeType = 0 LEFT OUTER JOIN MaterialProductIdValues mpv ON pav.AttributeValueId = mpv.AttributeValueId WHERE Product.ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#4 — line 762
```sql
SELECT ProductCategoryId FROM ProductRange pr INNER JOIN Product ON pr.ProductRangeId = Product.ProductRangeId WHERE Product.ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#5 — line 770
```sql
SELECT ProductCategoryId FROM ProductRange pr WHERE ProductRangeId = {Conversions.ToString(newrangeId)}
```

### ProductMaintenance.cs#6 — line 781
```sql
SELECT COUNT(*) AS cnt FROM ProductAttributeValues pav INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId WHERE pav.ProductId = {Conversions.ToString(productId)} AND attr.DisplayOrder > 1
```

### ProductMaintenance.cs#7 — line 789
```sql
SELECT COUNT(*) AS cnt FROM ProductOptionValues WHERE ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#8 — line 881
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### ProductMaintenance.cs#9 — line 884
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### ProductMaintenance.cs#10 — line 893
```sql
INSERT INTO PDMAudit.dbo.ProdCodeUpdates (TransactionId, ProductId, PrevProdCodeId, NewProdCodeId, SiteId) VALUES ({Conversions.ToString(num7)}, {Conversions.ToString(productId)}, {Conversions.ToString(num2)}, {Conversions.ToString(parseProductCode(Strings.Trim(DataGrid7[0, 3].ToString())))}, {Conversions.ToString(Global.SiteId(allowPLCOverride: true))})
```

### ProductMaintenance.cs#11 — line 905
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### ProductMaintenance.cs#12 — line 908
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### ProductMaintenance.cs#13 — line 919
```sql
INSERT INTO PDMAudit.dbo.ProductOCFS (TransactionId, ProductId, PrevOCFS, NewOCFS) VALUES ({Conversions.ToString(num8)}, {Conversions.ToString(productId)}, {text2}, {text5})
```

### ProductMaintenance.cs#14 — line 924
```sql
SELECT Status FROM Product WHERE ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#15 — line 937
```sql
SELECT Item FROM Item WHERE ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#16 — line 945
```sql
UPDATE Product SET Name = '{Strings.Trim(DataGrid1[0, 3].ToString())}',
```

### ProductMaintenance.cs#17 — line 1002
```sql
UPDATE Product SET CADPlaceProgram = NULL WHERE CADPlaceProgram = '' AND ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#18 — line 1005
```sql
UPDATE ProductDescription SET ShortDescription = '{DataGrid1[0, 3].ToString().Replace(} {,}{).Replace(} {,}{)
 .Trim()}' WHERE LanguageId = 1 AND DescriptionId IN (SELECT DISTINCT DescriptionId FROM Product WHERE ProductId = {Conversions.ToString(productId)})
```

### ProductMaintenance.cs#19 — line 1017
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### ProductMaintenance.cs#20 — line 1020
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### ProductMaintenance.cs#21 — line 1029
```sql
INSERT INTO PDMAudit.dbo.ProductUpdates (TransactionId, ProductId, PrevProduct, NewProduct) VALUES ({Conversions.ToString(num12)}, {Conversions.ToString(productId)}, '{text}', '{Strings.Trim(DataGrid2[0, 3].ToString())}')
```

### ProductMaintenance.cs#22 — line 1035
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### ProductMaintenance.cs#23 — line 1038
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### ProductMaintenance.cs#24 — line 1047
```sql
INSERT INTO PDMAudit.dbo.ProductOCFS (TransactionId, ProductId, PrevOCFS, NewOCFS) VALUES ({Conversions.ToString(num13)}, {Conversions.ToString(productId)}, 'prevRangeId = {Conversions.ToString(num)}', 'newRangeId = {Conversions.ToString(num5)}')
```

### ProductMaintenance.cs#25 — line 1081
```sql
SELECT ProductId, DescriptionId, 'Description:' AS Label, Name FROM Product WHERE ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#26 — line 1117
```sql
SELECT ProductId, DescriptionId, 'Product:' AS Label, Product FROM Product WHERE ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#27 — line 1153
```sql
SELECT Product.ProductId, Product.DescriptionId, 'Range:' AS Label, pc.Name + ' ~ ' + pr.Name AS Name FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId INNER JOIN ProductCategory pc ON pr.ProductCategoryId = pc.ProductCategoryId WHERE Product.ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#28 — line 1179
```sql
SELECT DISTINCT pc.Name + ' ~ ' + pr.Name AS Name FROM ProductRange pr INNER JOIN CatalogueProductRanges cpr ON pr.ProductRangeId = cpr.ProductRangeId INNER JOIN ProductCategory pc ON pr.ProductCategoryId = pc.ProductCategoryId WHERE cpr.CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### ProductMaintenance.cs#29 — line 1207
```sql
SELECT ProductId, DescriptionId, 'Format String:' AS Label, OrderCodeFormatString FROM Product WHERE ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#30 — line 1243
```sql
SELECT Product.ProductId, Product.DescriptionId, 'Image File:' AS Label, SUBSTRING(Product.ImageFile, 17, LEN(Product.ImageFile) - 16) AS ImageFile, Product.ImageFile AS FullImageFile FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE Product.ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#31 — line 1285
```sql
SELECT Product.ProductId, Product.DescriptionId, 'Wireframe:' AS Label, SUBSTRING(Product.WFImageFile, 19, LEN(Product.WFImageFile) - 18) AS WFImageFile, Product.WFImageFile AS FullWFImageFile FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE Product.ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#32 — line 1327
```sql
SELECT Product.ProductId, pc.ProductCodeId, 'Product Code:' AS Label, pc.Product_Code + ' | ' + pc.Description AS Product_Code FROM Product INNER JOIN Product_Code pc ON Product.ProductCodeId = pc.ProductCodeId WHERE Product.ProductId = {Conversions.ToString(productId)} AND SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}
```

### ProductMaintenance.cs#33 — line 1361
```sql
SELECT Product_Code, Description FROM Product_Code WHERE SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))} ORDER BY Product_Code
```

### ProductMaintenance.cs#34 — line 1389
```sql
SELECT ProductId, Status, 'Status:' AS Label, CASE WHEN Status = 0 THEN 'Unreleased (URL)' WHEN Status = 1 THEN 'Active (ACT)' WHEN Status = 2 THEN 'Obsolete (OBS)' WHEN Status = 3 THEN 'On Hold (HLD)' END AS StatusText FROM Product WHERE Product.ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#35 — line 1439
```sql
SELECT ProductId, CADAlias, 'Vis Category:' AS Label, CADAlias AS VisCategory FROM Product WHERE Product.ProductId = {Conversions.ToString(productId)}
```

### ProductMaintenance.cs#36 — line 1621
```sql
SELECT Site FROM Site WHERE SiteId = {Conversions.ToString(Global.SiteId(allowPLCOverride: true))}
```

## SelectorDialog.cs  (1)

### SelectorDialog.cs#1 — line 120
```sql
Select an option from the following list:
```

## SpareParts.cs  (4)

### SpareParts.cs#1 — line 576
```sql
SELECT cpc.ProductCategoryId, cpc.Name, CASE WHEN pc.Status <> 1 THEN pc.Status WHEN cpc.Status <> 1 THEN cpc.Status ELSE 1 END AS Status FROM CatalogueProductCategories cpc INNER JOIN ProductCategory pc ON cpc.ProductCategoryId = pc.ProductCategoryId WHERE CatalogueId = {_catalogueIdList[catalogue_selector.SelectedIndex].ToString()} ORDER BY DisplayOrder
```

### SpareParts.cs#2 — line 625
```sql
SELECT ItemId, Item FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE pr.Name LIKE '%{text}%' AND pr.Name <> '{category_selector.Text}' AND Item.Item NOT LIKE '%-%'
```

### SpareParts.cs#3 — line 676
```sql
SELECT DISTINCT child.ItemId, child.Item, ip.PartIndex, ip.Quantity FROM ItemParts ip INNER JOIN Item parent ON ip.ItemId = parent.ItemId INNER JOIN Item child ON ip.SubItemId = child.ItemId INNER JOIN Product ON child.ProductId = Product.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE ip.ItemId = {Conversions.ToString(num)} AND pr.ProductCategoryId = {_categoryIdList[category_selector.SelectedIndex].ToString()}
```

### SpareParts.cs#4 — line 737
```sql
SELECT Name, ImageFile FROM Product WHERE Product = '{parts_list.Items[parts_list.SelectedIndex].ToString()}'
```

## SparePartsTool.cs  (4)

### SparePartsTool.cs#1 — line 379
```sql
SELECT cpc.ProductCategoryId, cpc.Name, CASE WHEN pc.Status <> 1 THEN pc.Status WHEN cpc.Status <> 1 THEN cpc.Status ELSE 1 END AS Status FROM CatalogueProductCategories cpc INNER JOIN ProductCategory pc ON cpc.ProductCategoryId = pc.ProductCategoryId WHERE CatalogueId = 67 ORDER BY DisplayOrder
```

### SparePartsTool.cs#2 — line 394
```sql
SELECT ItemId, Item FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE pr.ProductCategoryId = {_categoryIdList[category_selector.SelectedIndex].ToString()} ORDER BY Item.Item
```

### SparePartsTool.cs#3 — line 435
```sql
SELECT ItemId, Item FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE pr.Name LIKE '%{text}%' AND pr.Name <> '{category_selector.Text}' AND Item.Item NOT LIKE '%-%'
```

### SparePartsTool.cs#4 — line 482
```sql
SELECT DISTINCT child.ItemId, child.Item, ip.PartIndex, ip.Quantity FROM ItemParts ip INNER JOIN Item parent ON ip.ItemId = parent.ItemId INNER JOIN Item child ON ip.SubItemId = child.ItemId INNER JOIN Product ON child.ProductId = Product.ProductId INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE ip.ItemId = {Conversions.ToString(num)} AND pr.ProductCategoryId = {_categoryIdList[category_selector.SelectedIndex].ToString()}
```

## TemplateForm.cs  (84)

### TemplateForm.cs#1 — line 730
```sql
SELECT DISTINCT OptionId FROM USOption
```

### TemplateForm.cs#2 — line 738
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 5 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#3 — line 751
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 1 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#4 — line 764
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 29 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#5 — line 777
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 6 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#6 — line 790
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 8 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#7 — line 804
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 7 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#8 — line 817
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 8 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#9 — line 830
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 31 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#10 — line 843
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 32 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#11 — line 856
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 33 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#12 — line 869
```sql
SELECT ShortDescription FROM OtherDescription WITH (NOLOCK) INNER JOIN DPSText ON OtherDescription.DescriptionId = DPSText.DescriptionId WHERE DPSText.DPSTextId = 34 AND OtherDescription.LanguageId = {Conversions.ToString(Global.languageId)}
```

### TemplateForm.cs#13 — line 972
```sql
SELECT TOP 1 datediff(day, t.TransactionDate, GetUTCDate()) AS days, datediff(hour, t.TransactionDate, GetUTCDate()) AS hours FROM PDMAudit.dbo.P{context.Substring(0, 1)}VUpdates pvu INNER JOIN PDMAudit.dbo.Transactions t ON pvu.TransactionId = t.TransactionId INNER JOIN {context}Value v ON pvu.{context}ValueId = v.{context}ValueId INNER JOIN Product ON pvu.ProductId = Product.ProductId INNER JOIN Item ON Product.ProductId = Item.ProductId INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = {Conversions.ToString(Global.catalogueId)} WHERE v.{context}Id = {Conversions.ToString(parentId)} ORDER BY t.TransactionDate DESC
```

### TemplateForm.cs#14 — line 999
```sql
SELECT TOP 1 datediff(day, t.TransactionDate, GetUTCDate()) AS days, datediff(hour, t.TransactionDate, GetUTCDate()) AS hours FROM PDMAudit.dbo.B{context.Substring(0, 1)}VUpdates bvu INNER JOIN PDMAudit.dbo.Transactions t ON bvu.TransactionId = t.TransactionId INNER JOIN {context}Value v ON bvu.{context}ValueId = v.{context}ValueId INNER JOIN CatalogueItems ci ON bvu.ItemId = ci.ItemId AND ci.CatalogueId = {Conversions.ToString(Global.catalogueId)} WHERE v.{context}Id = {Conversions.ToString(parentId)} ORDER BY t.TransactionDate DESC
```

### TemplateForm.cs#15 — line 1035
```sql
SELECT TOP 1 datediff(day, t.TransactionDate, GetUTCDate()) AS days, datediff(hour, t.TransactionDate, GetUTCDate()) AS hours FROM PDMAudit.dbo.C{context.Substring(0, 1)}VUpdates cvu INNER JOIN PDMAudit.dbo.Transactions t ON cvu.TransactionId = t.TransactionId INNER JOIN {context}Value v ON cvu.{context}ValueId = v.{context}ValueId WHERE v.{context}Id = {Conversions.ToString(parentId)} AND cvu.CatalogueId = {Conversions.ToString(Global.catalogueId)} ORDER BY t.TransactionDate DESC
```

### TemplateForm.cs#16 — line 1070
```sql
SELECT TOP 1 datediff(day, t.TransactionDate, GetUTCDate()) AS days, datediff(hour, t.TransactionDate, GetUTCDate()) AS hours FROM PDMAudit.dbo.D{context.Substring(0, 1)}VUpdates dvu INNER JOIN PDMAudit.dbo.Transactions t ON dvu.TransactionId = t.TransactionId INNER JOIN {context}Value v ON dvu.{context}ValueId = v.{context}ValueId INNER JOIN [{context}] f ON v.{context}Id = f.{context}Id INNER JOIN ProductCategory pc ON f.ProductCategoryId = pc.ProductCategoryId AND pc.ProductCategoryId = {Conversions.ToString(Global.categoryId)} WHERE v.{context}Id = {Conversions.ToString(parentId)} ORDER BY t.TransactionDate DESC
```

### TemplateForm.cs#17 — line 1207
```sql
SELECT AttributeValueId FROM ProductAttributeValues WITH (NOLOCK) WHERE ProductId = {Conversions.ToString(Global.productId)}
```

### TemplateForm.cs#18 — line 1777
```sql
SELECT attr.AttributeId, attr.DisplayOrder, attr.Name, attr.OrderCodeFormatKey FROM Attribute attr WITH (NOLOCK) INNER JOIN ProductCategory pc ON attr.ProductCategoryId = pc.ProductCategoryId WHERE pc.ProductCategoryId = {Conversions.ToString(Global.categoryId)} ORDER BY attr.DisplayOrder
```

### TemplateForm.cs#19 — line 1866
```sql
SELECT opt.OptionId, opt.DisplayOrder, opt.Name, opt.OrderCodeFormatKey FROM [Option] opt WITH (NOLOCK) INNER JOIN ProductCategory pc ON opt.ProductCategoryId = pc.ProductCategoryId WHERE pc.ProductCategoryId = {Conversions.ToString(Global.categoryId)} OR opt.OptionId IN (8, 28, 3344, 3346, 6790, 6791, 8512, 8513, 8524, 8525, 8624, 8625) ORDER BY opt.DisplayOrder
```

### TemplateForm.cs#20 — line 2056
```sql
SELECT ProductRangeId, OrderCodeFormatString FROM ProductRange WITH (NOLOCK) WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)}
```

### TemplateForm.cs#21 — line 2087
```sql
UPDATE ProductRange SET OrderCodeFormatString = '{text17}' WHERE ProductRangeId = {, arrayList4[j]))}
```

### TemplateForm.cs#22 — line 2092
```sql
INSERT INTO PDMAudit.dbo.Transactions (UserName, TransactionDate, DatabaseEffected) VALUES ('{Environment.UserName.ToLower()}', GetUTCDate(), '{Global.DBIdentity}')
```

### TemplateForm.cs#23 — line 2095
```sql
SELECT TOP 1 TransactionId FROM PDMAudit.dbo.Transactions WHERE UserName = '{Environment.UserName.ToLower()}' ORDER BY TransactionId DESC
```

### TemplateForm.cs#24 — line 2104
```sql
INSERT INTO PDMAudit.dbo.ProductRangeOCFS (TransactionId, ProductRangeId, PrevOCFS, NewOCFS) VALUES ({Conversions.ToString(num15)}, {, arrayList4[j]),}, '{), arrayList5[j].ToString()),}', '{), text17),}'){))}
```

### TemplateForm.cs#25 — line 2498
```sql
SELECT AttributeValueId FROM ProductAttributeValues WITH (NOLOCK)
```

### TemplateForm.cs#26 — line 2533
```sql
SELECT AttributeValueId FROM AttributeValue WITH (NOLOCK) WHERE AttributeId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#27 — line 2571
```sql
SELECT DISTINCT OptionId FROM [Option] WHERE OptionId = {Conversions.ToString(optionId)} AND OptionId IN (SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN ProductOptionValues pov ON optval.OptionValueId = pov.OptionValueId UNION SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN ProductRangeOptionValues prov ON optval.OptionValueId = prov.OptionValueId UNION SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN DependentAttributeValues dav ON optval.OptionValueId = dav.AdditionalOptionValueId UNION SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId UNION SELECT -1)
```

### TemplateForm.cs#28 — line 2722
```sql
SELECT optval.OptionId FROM OptionValue optval INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId WHERE dov.OptionValueId = {Conversions.ToString(-1 * num16)}
```

### TemplateForm.cs#29 — line 2830
```sql
UPDATE [Option] SET IsFabric = 1 WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#30 — line 2835
```sql
UPDATE [Option] SET IsFabric = 2 WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#31 — line 2840
```sql
UPDATE [Option] SET IsFabric = 0 WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#32 — line 2845
```sql
UPDATE [Option] SET IsFabric = -1 WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#33 — line 2852
```sql
SELECT DisplayOrder FROM [Option] WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#34 — line 2861
```sql
Select MAX(DisplayOrder) As maxDO FROM [Option] WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} And OptionId <> {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#35 — line 2872
```sql
UPDATE [Option] Set DisplayOrder = DisplayOrder - 1 WHERE DisplayOrder > {Conversions.ToString(num6)} And ProductCategoryId = {Conversions.ToString(Global.categoryId)} And DisplayOrder < 900
```

### TemplateForm.cs#36 — line 2876
```sql
UPDATE [Option] Set DisplayOrder = {Conversions.ToString(num7)} WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#37 — line 2890
```sql
SELECT MAX(DisplayOrder) AS maxDO FROM [Option] WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND OptionId <> {Conversions.ToString(_parentId)} AND DisplayOrder < 900
```

### TemplateForm.cs#38 — line 2899
```sql
UPDATE [Option] SET DisplayOrder = {Conversions.ToString(num23)} WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#39 — line 2995
```sql
SELECT Name, OrderCodeFormatKey, DisplayOrder FROM Attribute WITH (NOLOCK) WHERE AttributeId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#40 — line 3051
```sql
SELECT Name, OrderCodeFormatKey, DisplayOrder FROM Attribute WITH (NOLOCK) WHERE AttributeId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#41 — line 3070
```sql
Delete All Redundant Attributes{:
 {
 Cursor = Cursors.WaitCursor}
```

### TemplateForm.cs#42 — line 3076
```sql
SELECT DISTINCT AttributeId FROM Attribute WITH (NOLOCK) WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND AttributeId IN (SELECT DISTINCT AttributeId FROM AttributeValue atval WITH (NOLOCK) INNER JOIN ProductAttributeValues pav ON atval.AttributeValueId = pav.AttributeValueId UNION SELECT DISTINCT AttributeId FROM AttributeValue atval WITH (NOLOCK) INNER JOIN BaseAttributeValues bav ON atval.AttributeValueId = bav.AttributeValueId UNION SELECT -1)
```

### TemplateForm.cs#43 — line 3085
```sql
SELECT DISTINCT AttributeId FROM Attribute WITH (NOLOCK) WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND AttributeId NOT IN (SELECT DISTINCT AttributeId FROM AttributeValue atval WITH (NOLOCK) INNER JOIN ProductAttributeValues pav ON atval.AttributeValueId = pav.AttributeValueId UNION SELECT DISTINCT AttributeId FROM AttributeValue atval WITH (NOLOCK) INNER JOIN BaseAttributeValues bav ON atval.AttributeValueId = bav.AttributeValueId UNION SELECT -1)
```

### TemplateForm.cs#44 — line 3094
```sql
SELECT DISTINCT Notes FROM Item WHERE Notes IS NOT NULL
```

### TemplateForm.cs#45 — line 3133
```sql
Delete All Redundant Attributes{)}
```

### TemplateForm.cs#46 — line 3148
```sql
DELETE FROM CatalogueAttributeValues WHERE AttributeValueId IN (SELECT AttributeValueId FROM AttributeValue WHERE AttributeId IN ({Conversions.ToString(num13)}, -1) UNION SELECT -1)
```

### TemplateForm.cs#47 — line 3151
```sql
DELETE FROM DependentAttributeValues WHERE AttributeValueId IN (SELECT AttributeValueId FROM AttributeValue WHERE AttributeId IN ({Conversions.ToString(num13)}, -1) UNION SELECT -1)
```

### TemplateForm.cs#48 — line 3154
```sql
DELETE FROM HandbookAttributes WHERE AttributeId IN ({Conversions.ToString(num13)}, -1)
```

### TemplateForm.cs#49 — line 3157
```sql
DELETE FROM AttributeValue WHERE AttributeId IN ({Conversions.ToString(num13)}, -1)
```

### TemplateForm.cs#50 — line 3160
```sql
DELETE FROM Attribute WHERE AttributeId IN ({Conversions.ToString(num13)}, -1)
```

### TemplateForm.cs#51 — line 3167
```sql
SELECT AttributeId FROM Attribute WITH (NOLOCK) WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} ORDER BY DisplayOrder
```

### TemplateForm.cs#52 — line 3178
```sql
UPDATE Attribute SET DisplayOrder = {Conversions.ToString(num15 + 1)} WHERE AttributeId = {, arrayList13[num15]))}
```

### TemplateForm.cs#53 — line 3183
```sql
Delete All Redundant Attributes{)}
```

### TemplateForm.cs#54 — line 3190
```sql
Delete All Redundant Attributes{)}
```

### TemplateForm.cs#55 — line 3196
```sql
Delete All Redundant Attributes{)}
```

### TemplateForm.cs#56 — line 3213
```sql
SELECT CASE WHEN od.ShortDescription IS NULL THEN opt.Name ELSE od.ShortDescription END AS label FROM [Option] opt WITH (NOLOCK) INNER JOIN OtherDescription od ON opt.DescriptionId = od.DescriptionId AND od.LanguageId = 1 WHERE opt.OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#57 — line 3267
```sql
SELECT Name, OrderCodeFormatKey, DisplayOrder FROM [Option] WITH (NOLOCK) WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#58 — line 3310
```sql
SELECT Name, OrderCodeFormatKey, DisplayOrder FROM [Option] WITH (NOLOCK) WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#59 — line 3329
```sql
Delete All Redundant Options{:
 {
 Cursor = Cursors.WaitCursor}
```

### TemplateForm.cs#60 — line 3336
```sql
SELECT DISTINCT OptionId FROM [Option] WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND OptionId IN (SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN ProductOptionValues pov ON optval.OptionValueId = pov.OptionValueId UNION SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN ProductRangeOptionValues prov ON optval.OptionValueId = prov.OptionValueId UNION SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN DependentAttributeValues dav ON optval.OptionValueId = dav.AdditionalOptionValueId UNION SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId UNION SELECT -1)
```

### TemplateForm.cs#61 — line 3344
```sql
SELECT DISTINCT OptionId, Name FROM [Option] WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND OptionId NOT IN (SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN ProductOptionValues pov ON optval.OptionValueId = pov.OptionValueId UNION SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN ProductRangeOptionValues prov ON optval.OptionValueId = prov.OptionValueId UNION SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN DependentAttributeValues dav ON optval.OptionValueId = dav.AdditionalOptionValueId UNION SELECT DISTINCT OptionId FROM OptionValue optval INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId UNION SELECT -1)
```

### TemplateForm.cs#62 — line 3356
```sql
Delete All Redundant Options{)}
```

### TemplateForm.cs#63 — line 3367
```sql
Delete Redundant Options
```

### TemplateForm.cs#64 — line 3417
```sql
Delete All Redundant Options{)}
```

### TemplateForm.cs#65 — line 3423
```sql
Delete All Redundant Options{)}
```

### TemplateForm.cs#66 — line 3546
```sql
SELECT AttributeId, Name, DisplayOrder FROM Attribute WITH (NOLOCK) WHERE ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND AttributeId NOT IN (-1
```

### TemplateForm.cs#67 — line 3550
```sql
SELECT OptionId, Name, DisplayOrder FROM [Option] WITH (NOLOCK) WHERE (ProductCategoryId = {Conversions.ToString(Global.categoryId)} OR OptionId IN (8, 28, 3344, 3346, 6790, 6791
```

### TemplateForm.cs#68 — line 3942
```sql
SELECT ItemId FROM Item WITH (NOLOCK) WHERE Item = '{text}'
```

### TemplateForm.cs#69 — line 3954
```sql
DELETE FROM CatalogueItemExclusions WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ItemId = {Conversions.ToString(num)}
```

### TemplateForm.cs#70 — line 3960
```sql
INSERT INTO CatalogueItemExclusions (CatalogueId, ItemId) VALUES ({Conversions.ToString(Global.catalogueId)}, {Conversions.ToString(num)})
```

### TemplateForm.cs#71 — line 3993
```sql
SELECT ItemId FROM Item WITH (NOLOCK) WHERE Item = '{text}'
```

### TemplateForm.cs#72 — line 4003
```sql
SELECT ItemId FROM CatalogueItemExclusions WITH (NOLOCK) WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)} AND ItemId = {Conversions.ToString(num)}
```

### TemplateForm.cs#73 — line 4166
```sql
SELECT DISTINCT pov.ProductId, optval.OptionValueId, optval.Name, optval.OrderCodeValue FROM OptionValue optval WITH (NOLOCK) INNER JOIN Productoptionvalues pov ON optval.OptionValueId = pov.OptionValueId INNER JOIN DependentOptionValues dov ON optval.OptionValueId = dov.AdditionalOptionValueId
```

### TemplateForm.cs#74 — line 4174
```sql
SELECT IsFabric FROM [Option] WITH (NOLOCK) WHERE OptionId = {Conversions.ToString(_parentId)}
```

### TemplateForm.cs#75 — line 4192
```sql
SELECT AttributeValueId AS ValueId FROM DependentAttributeValues WITH (NOLOCK) WHERE AdditionalOptionValueId = {, arrayList2[j]),} UNION {),}SELECT OptionValueId AS ValueId FROM DependentOptionValues WITH (NOLOCK) WHERE AdditionalOptionValueId = {), arrayList2[j]))}
```

### TemplateForm.cs#76 — line 4286
```sql
Delete All Redundant Attributes{)}
```

### TemplateForm.cs#77 — line 4356
```sql
Delete All Redundant Options{)}
```

### TemplateForm.cs#78 — line 4385
```sql
SELECT IsFabric, DisplayOrder FROM [Option] WITH (NOLOCK) WHERE OptionId = {Conversions.ToString(int.Parse(Conversions.ToString(arrayList[0])))}
```

### TemplateForm.cs#79 — line 4632
```sql
SELECT DISTINCT Product.ProductId, Product.Product, Product.ProductRangeId, ci.CatalogueId, Product.NewProduct, Product.Status FROM Product WITH (NOLOCK) INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId INNER JOIN Item ON Product.ProductId = Item.ProductId INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = {Conversions.ToString(Global.catalogueId)} WHERE pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND Product.NewProduct = 0
```

### TemplateForm.cs#80 — line 4810
```sql
SELECT ProductId, Product FROM Product WITH (NOLOCK) INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId WHERE pr.ProductCategoryId = {Conversions.ToString(Global.categoryId)} AND pr.Status < 2 AND Product.Status < 2
```

### TemplateForm.cs#81 — line 5050
```sql
SELECT ShortDescription FROM OtherDescription od WITH (NOLOCK) INNER JOIN Attribute attr ON od.DescriptionId = attr.DescriptionId WHERE od.LanguageId = {Conversions.ToString(Global.languageId)} AND attr.AttributeId = {Conversions.ToString(attributeSelector.AttributeId)}
```

### TemplateForm.cs#82 — line 5129
```sql
SELECT ApplyUniqueOrderRules FROM Catalogue WITH (NOLOCK) WHERE CatalogueId = {Conversions.ToString(Global.catalogueId)}
```

### TemplateForm.cs#83 — line 5154
```sql
SELECT UniqueOrderFlag, Product FROM Product WITH (NOLOCK) INNER JOIN Item ON Product.ProductId = Item.ProductId WHERE Item.Item = '{_itemSelections.BaseItem[num3].ToString()}'
```

### TemplateForm.cs#84 — line 5183
```sql
SELECT UniqueOrderFlag, Product FROM Product WITH (NOLOCK) WHERE Product.ProductId = {Conversions.ToString(productId)}
```

## ValidateItemsThread.cs  (13)

### ValidateItemsThread.cs#1 — line 237
```sql
SELECT ProductCategoryId, OrderCodeFormatKey, Schemable FROM [Option] WHERE OptionId = {Conversions.ToString(num2)}
```

### ValidateItemsThread.cs#2 — line 261
```sql
SELECT ProductCategoryId, OrderCodeFormatKey FROM Attribute WHERE AttributeId = {Conversions.ToString(num3)}
```

### ValidateItemsThread.cs#3 — line 465
```sql
SELECT OrderCodeFormatString AS OCFS FROM ProductRange WHERE ProductCategoryId = {Conversions.ToString(num4)} AND Status = 1
```

### ValidateItemsThread.cs#4 — line 474
```sql
SELECT OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = {Conversions.ToString(_catalogueId)}
```

### ValidateItemsThread.cs#5 — line 482
```sql
SELECT OptionValueId FROM OptionValue WHERE ExcludeFromValidation = 0
```

### ValidateItemsThread.cs#6 — line 732
```sql
SELECT Product.Product, pc.Product_Code, cat.Name FROM Item CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x INNER JOIN Product ON Item.ProductId = Product.ProductId INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = {Conversions.ToString(_siteId)} INNER JOIN ProductRange rng ON Product.ProductRangeId = rng.ProductRangeId INNER JOIN ProductCategory cat ON rng.ProductCategoryId = cat.ProductCategoryId WHERE Item.ItemId = {, myparent._permItemIdList[num21]))}
```

### ValidateItemsThread.cs#7 — line 746
```sql
SELECT SubItemId FROM ItemComponents WHERE ItemId = {, myparent._permItemIdList[num21]))}
```

### ValidateItemsThread.cs#8 — line 763
```sql
SELECT DISTINCT optval.OptionValueId, optval.OrderCodeValue, optval.Name FROM OptionValue optval INNER JOIN ItemOptionValues itov ON optval.OptionValueId = itov.OptionValueId WHERE itov.ItemId = {, arrayList22[num23]))}
```

### ValidateItemsThread.cs#9 — line 843
```sql
EXEC spHM_GetListPrice '{text12}', '{text13}', 'UK', '01-Jan-2030', 'GBP', @list OUT, @valid OUT
```

### ValidateItemsThread.cs#10 — line 901
```sql
SELECT DISTINCT ProductId, Product, cpc.DisplayOrder FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId INNER JOIN CatalogueProductCategories cpc ON pr.ProductCategoryId = cpc.ProductCategoryId INNER JOIN CatalogueProductRanges cpr ON pr.ProductRangeId = cpr.ProductRangeId WHERE cpc.CatalogueId = {Conversions.ToString(_catalogueId)} AND cpr.CatalogueId = {Conversions.ToString(_catalogueId)} AND Product.Product LIKE '%{_itemFilter.Replace(}zzz{,}{)}%' AND (cpc.ProductCategoryId = {Conversions.ToString(_categoryId)} OR {Conversions.ToString(categoryId)} = -1) ORDER BY cpc.DisplayOrder, Product.Product
```

### ValidateItemsThread.cs#11 — line 915
```sql
SELECT DISTINCT attr.AttributeId, atval.AttributeValueId, attr.Name, attr.DisplayOrder, atval.DisplayOrdinal, /*CASE WHEN Item.Status <> 1 THEN Item.Status ELSE*/ Product.Status /*END AS Status*/ FROM AttributeValue atval INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId INNER JOIN ProductAttributeValues pav ON atval.AttributeValueId = pav.AttributeValueId INNER JOIN Product ON pav.ProductId = Product.ProductId /*INNER JOIN Item ON Product.ProductId = Item.ProductId */WHERE pav.ProductId = {_productIdList[num29].ToString()} AND atval.OrderCodeValue IS NULL AND atval.Status = 1 ORDER BY attr.DisplayOrder, atval.DisplayOrdinal
```

### ValidateItemsThread.cs#12 — line 954
```sql
SELECT AttributeValueId FROM CatalogueAttributeValues WHERE AttributeValueId = {arrayList24[num34].ToString()} AND CatalogueId = {Conversions.ToString(_catalogueId)}
```

### ValidateItemsThread.cs#13 — line 994
```sql
SELECT atval.AttributeValueId FROM ProductAttributeValues pav INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId WHERE pav.ProductId <> {_productIdList[num29].ToString()} AND atval.AttributeId = {Conversions.ToString(num31)} AND atval.Status = 1
```

## VerifyOptions.cs  (11)

### VerifyOptions.cs#1 — line 59
```sql
SELECT Name, LeadTime FROM Catalogue WHERE CatalogueId = {Conversions.ToString(catalogueId)}
```

### VerifyOptions.cs#2 — line 71
```sql
SELECT ProductId FROM Item WHERE Item = '{text4}'
```

### VerifyOptions.cs#3 — line 84
```sql
SELECT OptionValueId FROM CatalogueOptionValues WHERE CatalogueId = {Conversions.ToString(catalogueId)}
```

### VerifyOptions.cs#4 — line 92
```sql
SELECT cpoe.OptionValueId FROM CatalogueProductOptionExclusions cpoe INNER JOIN Product ON cpoe.ProductId = Product.ProductId WHERE Product.ProductId = '{Conversions.ToString(num4)}' AND cpoe.CatalogueId = {Conversions.ToString(catalogueId)}
```

### VerifyOptions.cs#5 — line 100
```sql
SELECT cioe.OptionValueId FROM CatalogueItemOptionExclusions cioe INNER JOIN Item ON cioe.ItemId = Item.ItemId WHERE Item.Item = '{text4}' AND cioe.CatalogueId = {Conversions.ToString(catalogueId)}
```

### VerifyOptions.cs#6 — line 120
```sql
SELECT DISTINCT USOptionValueId, OrderCodeValue FROM USOptionValue
```

### VerifyOptions.cs#7 — line 129
```sql
SELECT DISTINCT optval.USOptionValueId AS OptionValueId, opt.USOptionId AS OptionId, optval.OrderCodeValue AS OrderCodeValue2, 0 AS IsFabric, 1 AS Status FROM USOptionValue optval INNER JOIN USOption opt ON optval.USOptionId = opt.USOptionId INNER JOIN USItemOptionValues uitov ON optval.USOptionValueId = uitov.USOptionValueId INNER JOIN USItem ON uitov.USItemId = USItem.USItemId WHERE USItem.USItem = '{text4}' AND optval.OrderCodeValue NOT LIKE '%#'
```

### VerifyOptions.cs#8 — line 154
```sql
SELECT FeaturePositionString FROM ItemComponents itco INNER JOIN Item ON itco.SubItemId = Item.ItemId WHERE Item.Item = '{text4}' AND itco.ItemId = {Conversions.ToString(SPparentItemId)}
```

### VerifyOptions.cs#9 — line 172
```sql
SELECT DISTINCT '' AS Range2, -1 AS ProductId, '' AS Product2, opt.Name AS Option2, opt.DescriptionId AS optDescId, opt.OptionId AS OptionId, opt.OrderCodeFormatKey, optval.OptionValueId, optval.OrderCodeValue AS OrderCodeValue2, optval.Status, NULL AS ParentOptId, NULL AS ParentOptDescId, NULL AS ParentOptName, NULL AS ParentOptValId, NULL AS ParentOptValDescId, NULL AS ParentOptValName, NULL AS ParentOptValCode, NULL AS ParentOptIsFabric, NULL AS ParentDisplayOrder, opt.DisplayOrder, opt.EOSLiteDisplayOrder, optval.DisplayOrdinal, opt.TertiaryOption, opt.IsFabric, optval.Name AS optval_name, optval.DescriptionId AS optvalDescId, optval.ImageFile, opt.ProductCategoryId, '' AS PriceBand FROM OptionValue optval INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId WHERE opt.OptionId IN (-1,
```

### VerifyOptions.cs#10 — line 469
```sql
SELECT COUNT(*) AS cnt FROM CatalogueOptionValues WHERE OptionValueId = {, arrayList3[num20]),} AND CatalogueId = {), catalogueId))}
```

### VerifyOptions.cs#11 — line 483
```sql
SELECT OptionValueId, OrderCodeValue FROM OptionValue WHERE OptionValueId = {, arrayList3[num20]))}
```

## VerifyOrders.cs  (1)

### VerifyOrders.cs#1 — line 94
```sql
SELECT ProductId as prod_id FROM Product WHERE Product = '{text5}' OR Product = '{text6}'
```
