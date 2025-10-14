目前的项目需求：
第一步是先尝试把后端接口写完，推荐用fastapi+postgresql的技术栈，建议用vibe coding配合着写，后端人工写，前端AI写。
数据表建议这么设计：
user——chat——message，各自都有增删查改的接口，一对多的关系
domain——document——chunk，同样，各自有增删查改。然后这里的chunk存实际的文档chunk内容，向量数据库里只存id+向量，检索到向量后，再从postgresql里的chunk表里取string，domain就是指不同来源，方便做带有filter的检索
大概需要提供的api有：
用户登录注册（需要区分admin权限，用一个字段标记admin，初始admin用sql强制写入就行）
问答的增删查改
资料管理的增删查改
api可能不好想齐全，那么可以让AI帮忙设计界面后，再反过来想需要什么样的api去满足界面交互
