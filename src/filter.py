import json
import psycopg2 as pypgsql
import os
import geopandas as gpd
from matplotlib import axes

class Filter:
    """
    过滤器类定义
    """
    wenchangGEOJSON = {
        "type": "Polygon",
        "coordinates": [
          [
            [
              110.48469543457031,
              20.07205559050614
            ],
            [
              110.53138732910156,
              20.045610827439717
            ],
            [
              110.57189941406249,
              19.998515226890117
            ],
            [
              110.62065124511719,
              19.92881370407609
            ],
            [
              110.65567016601562,
              19.870705603320513
            ],
            [
              110.68244934082031,
              19.835830512275315
            ],
            [
              110.66116333007812,
              19.8203280126295
            ],
            [
              110.63232421875,
              19.802239852183064
            ],
            [
              110.61103820800781,
              19.740207700221667
            ],
            [
              110.621337890625,
              19.71435385099788
            ],
            [
              110.5945587158203,
              19.718878576562236
            ],
            [
              110.60142517089844,
              19.684616755836014
            ],
            [
              110.64743041992188,
              19.644527586685598
            ],
            [
              110.62545776367186,
              19.598606721590237
            ],
            [
              110.61927795410156,
              19.543613800253794
            ],
            [
              110.56777954101562,
              19.534554343674948
            ],
            [
              110.55267333984375,
              19.577905706819973
            ],
            [
              110.50529479980469,
              19.578552653812785
            ],
            [
              110.44761657714844,
              19.538437030170574
            ],
            [
              110.45379638671874,
              19.496369623182837
            ],
            [
              110.51422119140625,
              19.48601289077924
            ],
            [
              110.53413391113281,
              19.440046902565864
            ],
            [
              110.54718017578125,
              19.400544598624666
            ],
            [
              110.59318542480469,
              19.341597106309134
            ],
            [
              110.66459655761717,
              19.36491954229774
            ],
            [
              110.73188781738281,
              19.368158505739146
            ],
            [
              110.80604553222656,
              19.39601093343177
            ],
            [
              110.9296417236328,
              19.530024424775405
            ],
            [
              111.08207702636719,
              19.61671792534097
            ],
            [
              111.01959228515625,
              19.879746041940486
            ],
            [
              110.99212646484374,
              20.010129150846307
            ],
            [
              110.92208862304686,
              20.040450354169483
            ],
            [
              110.81222534179688,
              20.06173621322714
            ],
            [
              110.6927490234375,
              20.180367997317568
            ],
            [
              110.64262390136719,
              20.16941122761028
            ],
            [
              110.48469543457031,
              20.07205559050614
            ]
          ]
        ]
    }
    
    def _getGeoJSON(self):
        """
        从数据库获取边界数据，将其外包矩形转化为PL API能够识别的简单geojson格式
        """
        conn = None
        # new a connection object
        conn_str = "dbname = 'wenchang_19n' user = 'deyu' host = 'localhost' password = 'admin123'"
        conn = pypgsql.connect(conn_str)
        print("CONNECT succeed")
        sql = "SELECT geom FROM wenchang_bound"
        gdf = gpd.GeoDataFrame.from_postgis(sql, conn)#, crs='epsg:4326')
        bbox = gdf.envelope
        gpd.GeoSeries.plot(bbox)
        jsonObj = self._wktToPLGeoJSON(str(bbox[0]))
        return jsonObj

    def _wktToPLGeoJSON(self, wktStr):
        """
        将wkt文本转化为PL可以识别的geojson格式
        """
        if wktStr.startswith("POLYGON (("):
            if '),' not in wktStr:
                coordsList = []
                for pnt in wktStr[10:-2].split(', '):
                    pnts = []
                    for coord in pnt.split(' '):
                        pnts.append(float(coord))
                        coordsList.append(pnts)
            else:
                print("CAN NOT HANDLE ISLAND POLYGON")
        else:
            print("NOT VALID POLYGON WKT")
        coordinates =[]
        coordinates.append(coordsList)
        reJSON = {}
        reJSON["type"] = "Polygon"
        reJSON["coordinates"] = coordinates
        return reJSON
    def filterGenerator(self, geomUserMeth):
        """
        用于查询数据的查询条件配置
        :param geomUserMeth string 空间区域用户输入方法
        :return redding_reservoir geojson 查询条件的geojson形式返回

        """
        geo_json_geometry = {}
        if geomUserMeth == 'admin':
            geo_json_geometry = self._getGeoJSON()
        elif geomUserMeth == 'draw':
            geo_json_geometry = self.wenchangGEOJSON #先写死
        
        # 空间窗口过滤
        geometry_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": geo_json_geometry
        }

        # 时间窗口过滤
        date_range_filter = {
            "type": "DateRangeFilter",
            "field_name": "acquired",
            "config": {
                "gte": "2019-01-01T00:00:00.000Z",
                "lte": "2019-04-01T00:00:00.000Z"
            }
        }
        
        # 分辨率窗口过滤
        resolution_filter = {
            "type": "RangeFilter",
            "field_name": "pixel_resolution",
            "config": {
                "gte": 0,
                "lte": 100
            }
        }

        # 整合的过滤器，可以用来执行quick-search和创建saved-search（均为POST接口）
        generated_filters = {
            "type": "AndFilter",
            "config": [geometry_filter, date_range_filter, resolution_filter]
        }
        
        return generated_filters