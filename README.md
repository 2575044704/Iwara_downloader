# Iwara批量爬虫脚本
### 脚本适用于爬取大量Iwara视频使用
### 成果展示(36.1TB数据): [huggingface](https://huggingface.co/datasets/AnimeFans/Iwara_MMD_all)
----
# 脚本说明
## 按顺序执行:
- iwara.py: 按照发布时间,抓取视频元数据JSON,这个JSON将会是一个很大的文件.你可以修改爬取的页数
- extract.py, see_json.py:快速查看大JSON文件中的前N个视频信息,两个脚本略有区别,自己看代码
- separate_videos.py: 清洗iwara.py产生的JSON巨大元数据,例如无id的视频.否则影响后面爬虫
- json_classification.py:将大JSON文件中的视频按月份分类，每个视频保存为独立的JSON文件
- iwara_batch_downloader.py:从JSON中读取视频ID,发往下载函数.确保你的主机可以连上iwara
- pack.sh: 打包视频(可选)
## 其它脚本:
- fliter.py: 用于筛选和分析特定类型的视频
- calculate.py:计算大json视频元数据总大小
