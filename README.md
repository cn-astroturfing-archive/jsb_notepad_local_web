# README

关于网评员专用app记事本的介绍，请参考

https://hackmd.io/@g_aydPBHS1m5-pMA-nIfjw/HkXzPkT7Wl 


## 下载代码

本repo已经提供了repo创建时下载好的代码。下载方法供参考。

### 下载图片

**需要中国大陆ip**

运行

```bash
python3 download_images_keep_path.py --out imgs
```

下载结果保留url文件夹结构

```
imgs/
  jsb.notebookvip.cn/
    jsb-files/default_img/zhuanlan_01.png
    jsb-files/applogo/weibo.png
    jsb-wap/static/img/login.e154576.png
  img01.yzcdn.cn/
    vant/coupon-empty.png
    upload_files/2020/06/24/FmKWDg0bN9rMcTp9ne8MXiQWGtLn.png
```


### 下载css与js

**需要中国大陆ip**

`runtime-url`来自运行以下指令得到的html

```bash
curl https://jsb.notebookvip.cn/jsb-wap/
```

使用正确的`runtime-url`，运行以下命令(或者使用`./run.sh`)下载记事本代码。

```bash
python3 download_notebookvip_assets.py \
  --runtime-url "https://jsb.notebookvip.cn/jsb-wap/static/js/runtime.d6390d3ff74ff4e0029d.js" \
  --out jsb \
  --public-path "/jsb-wap/"
````

## 本地试玩

在包含`jsb_web`目录的目录中，运行python server
```bash
python3 -m http.server 8000
```

网站在`http://127.0.0.1:8000/jsb-wap/`即可访问。

打开浏览器控制台，在console粘贴代码，即可本地体验记事本界面。

初始化

```javascript
let vm = document.querySelector("#app").__vue__
const store = vm.$router.app.$options.store;

store.state.userInfo = vm.$store.state.userInfo || {}
store.state.userInfo.token = store.state.userInfo.token || "dummy-token";

store.state.userInfo.username = vm.$store.state.userInfo.username || "中央网信办"   //username控制水印
store.state.userInfo.roles = ["SUPER_ADMIN"]

store.state.userInfo.permissions = ["__DUMMY__"]; //不能空，否则会直接 NonPermissionTip
store.state.userInfo.permissions.includes = () => true; // 让所有权限检查都通过
```

列举所有可跳转的页面

```javascript
vm.$router.options.routes
  .filter(r => r && r.name)
  .map(r => ({
    name: r.name,
    path: r.path,
    title: r.meta && r.meta.title,
    allow: r.meta && r.meta.allow,
    allowNonAppVisit: r.meta && r.meta.allowNonAppVisit,
    pageLevel: r.meta && r.meta.pageLevel,
    activeNav: r.meta && r.meta.activeNav
  }))
```


可跳转的UI页

```javascript
vm.$router.replace({ name: "Protocol" })                  // 用户协议
vm.$router.replace({ name: "Secret" })                    // 隐私政策

vm.$router.replace({ name: "GatherInformation" })         // 收集信息清单
vm.$router.replace({ name: "SharedInformation" })         // 第三方共享清单

vm.$router.replace({ name: "TasksHome", query: { type: 1 } })   // 首页壳（path="/")
vm.$router.replace({ name: "TasksIndex" })                      // 头条
vm.$router.replace({ name: "TasksSquare" })                     // 时事
vm.$router.replace({ name: "TasksLocation" })                   // 主场
vm.$router.replace({ name: "My" })                              // 我的

vm.$router.replace({ name: "MyNotice" })                        //我的通知
vm.$router.replace({ name: "MyNoticeDetail" })


vm.$router.replace({ name: "Help" })                           //***帮助***
vm.$router.replace({ name: "Tutorials" })  
vm.$router.replace({ name: "PermissionManage" })


vm.$router.replace({ name: "TaskDetail", params: { id: "1" } }) //传播分析
vm.$router.replace({ name: "UploadDetails", params: { id: "1" } }) //截图详情

vm.$router.replace({ name: "SpecialColumnDetails" })           //专栏详情
vm.$router.replace({ name: "SpecialColumnUpload" })            //上传图片
vm.$router.replace({ name: "SpecialColumnUploaded" })          //已上传图片
vm.$router.replace({ name: "SpecialColumnStatistics" })        //传播统计
vm.$router.replace({ name: "SpecialColumnArticleDetails" })    //文章详情
vm.$router.replace({ name: "ColumnManagement" })               // 专栏管理
vm.$router.replace({ name: "ColumnPublish" })                  // **创建专栏**
vm.$router.replace({ name: "ArticlePublish" })                 // **文章发布**
vm.$router.replace({ name: "ColumnArticleManagement" })        // 专栏文章管理


vm.$router.replace({ name: "CreateIndex" })               // 我的创作
vm.$router.replace({ name: "CreateProps" })               // 属性设置
vm.$router.replace({ name: "CreateProtocol" })            // 投稿版权要求
vm.$router.replace({ name: "UploadOutline" })             // 上传大纲


vm.$router.replace({                                      //制作稿件
  name: "CreateAdd",
  params: { actId: "1", type: "1", id: "1" }
})

vm.$router.replace({                                      //稿件预览
  name: "CreatePreview",
  params: { id: "1" }
})

vm.$router.replace({ name: "TodoList" })                  // 审核中心
vm.$router.replace({ name: "TodoDetail", params: { id: "1" } }) //审核详情



vm.$router.replace({ name: "HeroesIndex" })               // 英雄榜

vm.$router.replace({
  name: "ArticleRank",
  params: { id: "1" }
})

vm.$router.replace({ name: "AreaRank" })                  //部门排名

vm.$router.replace({ name: "StatisticsIndex" })           // **任务统计**
vm.$router.replace({ name: "StatisticsDescription" })     // ***统计说明***

vm.$router.replace({ name: "IntegralInfos" })             // 积分明细
vm.$router.replace({ name: "UploadList" })                // 补录详情



vm.$router.replace({ name: "UserInfo" })                  // 设置
vm.$router.replace({ name: "FirstSet" })                  // 首次设置

vm.$router.replace({ name: "ModPassword" })
vm.$router.replace({ name: "ModPasswordNeedOld" })
vm.$router.replace({ name: "ModPasswordNeedVerifyCode" })

vm.$router.replace({ name: "ModPhone" })
vm.$router.replace({ name: "ModNickname" })
vm.$router.replace({ name: "BindAccount" })


vm.$router.replace({ name: "Login" })

vm.$router.replace({ name: "gestureSetting" })            // 设置手势密码
vm.$router.replace({ name: "gestureLogin" })              // 手势登录

vm.$router.replace({ name: "FingerPrintLogin" })          // 指纹登录
vm.$router.replace({ name: "FingerPrint" })               // 解锁设置


vm.$router.replace({ name: "Feedback" })
vm.$router.replace({ name: "FeedbackList" })
vm.$router.replace({ name: "FeedbackDetail" })
vm.$router.replace({ name: "FeedbackReply" })
vm.$router.replace({ name: "FeedbackAdd" })
vm.$router.replace({ name: "FeedbackActivityView" })
vm.$router.replace({ name: "FeedbackProvideMobile" })

vm.$router.replace({ name: "Tipoff" })                    // 举报投诉
vm.$router.replace({ name: "Contact" })                   // 联系我们


vm.$router.replace({ name: "SignUpList" })                //创作之星活动

vm.$router.replace({
  name: "SignUpForm",
  params: { actId: "1" }
})

vm.$router.replace({ name: "SignUpWang" })               //人气之星活动


vm.$router.replace({ name: "CourseIndex" })
vm.$router.replace({ name: "CourseSeries" })
vm.$router.replace({ name: "CourseDetail" })


vm.$router.replace({ name: "Search" })
vm.$router.replace({ name: "JumpMidPage" })
vm.$router.replace({ name: "ImgContentView" })


vm.$router.replace({ name: "ShareBlank" })
vm.$router.replace({ name: "404" })
vm.$router.replace({ name: "NonAppVisitTip" })         //请使用app访问
vm.$router.replace({ name: "NonPermissionTip" })


vm.$router.replace({ name: "Test" })
```

重置
```javascript
// 1) 清空 localStorage / sessionStorage
localStorage.clear();
sessionStorage.clear();

// 2) 清空 cookie
document.cookie.split(";").forEach(c => {
  document.cookie =
    c.trim().split("=")[0] +
    "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
});

// 3) 重置 Vuex userInfo（内存态）
if (vm?.$store?.state?.userInfo) {
  vm.$store.state.userInfo = {};
}

// 4) 刷新页面（重新加载整个 SPA）
location.reload();
```