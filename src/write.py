import fiona
from shapely.geometry import mapping

def writeJSON(cover_result):
    """
    输出覆盖结果报表，并将覆盖结果写入GeoJSON
    """
    from collections import OrderedDict
    cover_schema = {
        'geometry':'Polygon',
        'properties':OrderedDict([
            ('id', 'str'),
            ('res', 'int'),
            ('cloud', 'float')
        ])
    }
    
    from fiona.crs import from_epsg
    cover_crs = from_epsg(4326)

    output_driver = "GeoJSON"

    print("Begin Write Results!")
    
    with fiona.open(
        'test.json',
        'w',
        driver = output_driver,
        crs = cover_crs,
        schema = cover_schema) as f:
        for i in range(len(cover_result)):
            sample = cover_result[i]
            cover_sample = {
                'geometry': mapping(sample['geom']),
                'properties': OrderedDict([
                    ('id', sample['id']),
                    ('res', str(sample['res'])),
                    ('cloud', sample['cloud'])
                ])
            }
            f.write(cover_sample)
    
    # 显示
    from geojsonio import display
    with open('test.json') as f:
        contents = f.read()
        display(contents)   
