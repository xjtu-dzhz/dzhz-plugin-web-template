# 岱宗盒子 · web 插件模板

web 插件不是一个 App：它就是一个 zip 包，里面声明「用盒子内置浏览器打开哪个网页」。盒子打开它的时候走自己的浏览器，缓存、Cookie、夜间模式、下载都和盒子其它网页一致。

适合做「某个网页版服务在盒子里有个入口」这种事：图书馆预约、办事大厅、教务系统……

> 这个仓库是 GitHub **模板仓库**，点右上角 "Use this template" 复制一份就能开始改。

## 三步

**1. 改身份**

`plugin.manifest.json` 里：

| 字段 | 说明 |
|---|---|
| `id` | 小写字母开头，2–32 位，能带 `.` `_`，例如 `top.dzhz.plugin.library` |
| `name` | 1–14 个字（详情页顶栏放得下） |
| `summary` | 一句话简介，列表页最多三行 |
| `author` | 名字 + 主页 |
| `version` / `versionCode` | 每次发版 `versionCode` 必须变大 |

**2. 配网页**

`web` 段：

```json
"web": {
  "startUrl": "https://ehall.xjtu.edu.cn/",
  "origins": ["https://ehall.xjtu.edu.cn"],
  "allowSubdomains": true,
  "capabilities": ["theme"],
  "vpn": "optional_on"
}
```

| 字段 | 说明 |
|---|---|
| `startUrl` | 打开插件时加载的地址，必须是 https |
| `origins` | 允许停留的站点（scheme + host）。跳到别的主机会被拦下，只查主框架导航，子资源不管 |
| `allowSubdomains` | 是否连子域名一起放行 |
| `capabilities` | 宿主能给网页的能力，目前只认 `theme` |
| `vpn` | 见下面 |

**`vpn` 四档**（WebVPN 是校内的校外访问网关，开了校外在也能进校内站点）：

| 值 | 含义 |
|---|---|
| `required` | 必须走 VPN，用户不能关 |
| `optional_on` | 可选，默认开 |
| `optional_off` | 可选，默认关 |
| `off` | 必须直连，用户不能开 |

用户可以在插件详情页里改「可选」那两档。**走 VPN 时页面全在 `webvpn.xjtu.edu.cn` 下，原始域名被加密在路径里，所以 `origins` 只能按网关放行**——想严格限制站点，就别开 VPN。

**3. 打包**

```bash
python3 package.py            # 生成 <id>-<version>.zip
```

产物在仓库根目录。装进盒子：**插件 → 右上角设置 → 从文件安装**。

## 随包文件

`extra/` 目录里的东西会原样打进包，插件里用 `ctx.openPackageFile("文件名")` 读。图标、说明、示例数据都可以这么带。

## 签名与更新

盒子对插件用 TOFU：**第一包装进来时记住签名者**（公钥 SPKI 的 sha256），之后同一个 `id` 的更新必须用同一把私钥签、`versionCode` 更大，否则拒装。

- `signing/plugin-ec.pem` 是你的身份，**别弄丢**，也不要提交（`.gitignore` 已经挡了）；
- 换机器就把这把钥匙拷过去；CI 里用仓库 Secret `PLUGIN_SIGNING_KEY` 存它；
- 想换钥匙只能让用户先卸载再重装。

## 自动构建

`.github/workflows/build.yml`：

- **每次 push** → 构建 zip 传到这次运行的 Artifacts 里；
- **手动 Run workflow** → 同上，而且会**发到 Release**（需要一个 `v*` 形式的 tag 或手填版本）。

没配 `PLUGIN_SIGNING_KEY` 时会临时生成一把钥匙并给出警告——那种产物只能自己试试，别发给别人（下次构建签名就变了）。

## 注意

web 插件不跑代码，只加载网页，所以风险比 dex 插件小；但它仍然能通过登录态访问校内账号信息——只装你信任来源的插件。
