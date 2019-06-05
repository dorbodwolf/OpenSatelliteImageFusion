from search import Search
from cover import Cover
from write import writeJSON

if __name__ == "__main__":
    items = []
    # with open('_tmp_results_list.txt', 'w') as f:
    #     for item in items:
    #         f.write(str(item) +"\n")
    try:
        print("尝试读取保存下来的结果列表...")
        with open("_tmp_results_list.txt", "r") as f:
            for line in f:
                item = line.strip()
                import ast
                item_dict = ast.literal_eval(item) # 将字符串中的字典提出来，即：  "{...}" --> {...}
                items.append(item_dict)
    except Exception as e:
        print("无保存的查询结果，运行新的查询...")
        s = Search() #实例化查询类
        s.runSearch() #调用查询方法
        items = s.itemList #获取查询返回的结果列表
    c = Cover(items)
    cover_result = c.makeCover()
    writeJSON(cover_result)