from filter import Filter
from GeoMetDemo import dumps as dumpWKT
from shapely import wkt
import numpy as np
import copy

class Cover:
    """
    指定空间范围、时间范围和分辨率范围的最优影像覆盖分析
    """
    items = []
    def __init__(self, itemList):
        self.items = itemList

    def _round_coordinates(self, geomObj):
        """
        对几何体点集的坐标进行四舍五入降低精度
        """
        from shapely.geometry import shape, mapping
        geomJSON = mapping(geomObj)
        geomJSON['coordinates'] = np.round(np.array(geomJSON['coordinates'], dtype=float), 4)
        return shape(geomJSON)
    
    def _unionShapelyObjLists(self, shapelyObjList):
        """
        将一个shapely对象列表进行union运算为一个整的shapely对象
        :param list shapelyObjList shapely对象的列表
        :return object unionObj 返回union的shapely对象
        """
        # DEBUG 列表只有一个元素则直接返回
        if len(shapelyObjList) == 1:
            return shapelyObjList[0]
        unionObj = shapelyObjList[0].union(shapelyObjList[1])
        for i in range(2,len(shapelyObjList)):
            unionObj = unionObj.union(shapelyObjList[i])
        return unionObj
    
    def makeCover(self):
        """
        最优覆盖分析（初级）——利用系统云量
        """
        f = Filter()
        initGeom = f.wenchangGEOJSON
        initGeom = wkt.loads(dumpWKT(initGeom))
        initRes = 1000
        initCloud = 1
        initID = ''
        initItem = {'id':initID, 'geom':initGeom, 'res': initRes, 'cloud':initCloud}
        checkedItemList = []
        checkedItemList.append(initItem)
        uncheckedItems = self.items
        
        # 遍历查询结果来填入查询区域的边界范围内
        # 采用对每个api返回的查询结果item逐步进入的覆盖策略
        ### 这个地方相交查询可以用RTree来提高查询效率
        # from rtree import index
        # idx = index.Index()
        for uncheckedItem in uncheckedItems:
            uncheckedID = uncheckedItem['id']
            uncheckedRes = uncheckedItem['properties']['pixel_resolution']
            uncheckedCloud = uncheckedItem['properties']['cloud_cover']
            uncheckedGeom = uncheckedItem['geometry']
            uncheckedGeom = wkt.loads(dumpWKT(uncheckedGeom)) # 加载成shapely geometry对象
            updatedCheckedList = []
            print("Begin Checking " + uncheckedID + " ,Checked Item Now is {}".format(len(checkedItemList)))
            for checkedItem in checkedItemList:
                if checkedItem['geom'].area < 1e-3: # 这个阈值很关键，太大会漏，太小会拖垮程序
                    # continue
                    # DEBUG
                    updatedCheckedList.append(checkedItem)
                    continue
                # DEBUG：对所有多边形做buffer来避免拓扑错误，不论多边形大小
                # checkedItem['geom'] = self._round_coordinates(checkedItem['geom'])
                checkedItem['geom'] = checkedItem['geom'].buffer(1e-6)
                try:
                    if checkedItem['geom'].intersects(uncheckedGeom):
                        intersectGeom = checkedItem['geom'].intersection(uncheckedGeom)
                        # DEBUG 如果待插入的item与存在的块相交面积太小，则不去急着更新块,因为这是碎块产生太多的根本原因
                        if intersectGeom.area < 1e-4:
                            updatedCheckedList.append(checkedItem)
                            continue
                        # 待插入数据与存在数据的象元尺寸相同
                        if uncheckedRes == checkedItem['res']:
                            if uncheckedCloud < checkedItem['cloud']:
                                intersectItem = {'id':uncheckedID, 'geom':intersectGeom, 'res': uncheckedRes, 'cloud':uncheckedCloud}
                            else:
                                # DEBUG：要拷贝，而不是赋值
                                intersectItem = copy.copy(checkedItem)
                                intersectItem['geom'] = intersectGeom
                        # 待插入数据的象元尺寸大于存在数据的象元尺寸
                        elif uncheckedRes > checkedItem['res']:
                            if uncheckedCloud - checkedItem['cloud'] < -0.2:
                                intersectItem = {'id':uncheckedID, 'geom':intersectGeom, 'res': uncheckedRes, 'cloud':uncheckedCloud}
                            else:
                                intersectItem = copy.copy(checkedItem)
                                intersectItem['geom'] = intersectGeom
                        # 待插入数据的象元尺寸小于存在数据的象元尺寸（分辨率更高）
                        else:
                            # 待插入数据云量不比存在数据高很多，就插入替换重叠区域
                            if uncheckedCloud - checkedItem['cloud'] <= 0.02:
                                intersectItem = {'id':uncheckedID, 'geom':intersectGeom, 'res': uncheckedRes, 'cloud':uncheckedCloud}
                            else:
                                intersectItem = copy.copy(checkedItem)
                                intersectItem['geom'] = intersectGeom
                        updatedCheckedList.append(intersectItem)
                        differenceGeom = checkedItem['geom'].difference(intersectGeom)
                        # 修复bug 添加差值区域为空的判断条件
                        # 如果重叠区域外还有未确认区域，就将未确认区域继续加入判断列表
                        if differenceGeom.area > 0.0:
                            DifferenceItem = {'id':checkedItem['id'], 'geom':differenceGeom, 'res': checkedItem['res'], 'cloud':checkedItem['cloud']}
                            updatedCheckedList.append(DifferenceItem)
                    else:
                        updatedCheckedList.append(checkedItem)
                except Exception:
                    # DEBUG shapely.errors.PredicateError
                    # DEBUG 相交运算拓扑错误引发异常
                    # from geojsonio import display
                    # display(uncheckedGeom)
                    print("致命的GEOS错误！")
                    exit(0)
                else:
                    pass
            # 按id合并checkedItemList的元素
            print("--Checked Item Now is {}".format(len(updatedCheckedList))  + " ,Begin Merging Items by ID")
            import pandas as pd 
            mergedUpdatedCheckedList = [{'id': name, 'geom':self._unionShapelyObjLists([geom for geom in group.geom]), \
                'res': group['res'].iloc[0], 'cloud': group.cloud.iloc[0]} \
                for name, group in pd.DataFrame(updatedCheckedList).groupby(['id'])]
            checkedItemList = []
            checkedItemList = mergedUpdatedCheckedList
            print("--End Merging Items by ID!" + " Checked Item Now is {}".format(len(checkedItemList)))
        
        print("Begin Processing return Item List")
        # 将结果item中的multipolygon分解为polygon
        splitItemList = []
        for item in checkedItemList:
            print(item['geom'].type)
            if item['geom'].type == 'MultiPolygon':
                for poly in item['geom']:
                    item_split = {'id':item['id'], 'geom':poly, 'res': item['res'], 'cloud':item['cloud']}
                    splitItemList.append(item_split)
            elif item['geom'].type == 'Polygon':
                splitItemList.append(item)
            # 严谨的异常处理
            else:
                print("ERROR GEOMETRY TYPE THAT CANNOT HANDLE BY SPLIT")
        print("===拆分复合多边形===")
        for item in splitItemList:
            print(item['geom'].type)

        print("End Processing return Item List")
        return splitItemList




