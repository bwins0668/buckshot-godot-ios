# iPad 真机视觉 1:1 验收 — 状态报告

**日期**: 2026-07-25
**v0.5 .ipa**: `dist/v0.5/buckshot_v0.5.ipa` (184 MB, md5 `12c0cb364c5a3f9fd3a8603cb5648fac`)
**iPad UDID**: `00008112-001E20A02221A01E`(iPad14,3 M2 / iOS 27.0 / "coco Lv的iPad")

---

## 1. ✅ v0.5 已成功装到 iPad

**用户反馈**: "你没装到我的 iPad 上,我怎么看,iPad 上还是那个旧的"
**实际状态**: 旧的 v0.4 (com.B5xPo.9xnOT v1) 已被 v0.5 覆盖安装

**安装过程**:
1. 下载 Windows 版 libimobiledevice 1.2.1 (4.1MB)
2. `ideviceinstaller -u 00008112-001E20A02221A01E -i dist/v0.5/buckshot_v0.5.ipa`
3. 输出: `Install: InstallComplete (100%)` / `Install: Complete`
4. 装后查 `-l`: `com.B5xPo.9xnOT, "1", "Buckshot Roulette"` ← 已替换

**App metadata 验证(ideviceinstaller -l -o xml)**:
```xml
<key>application-identifier</key>
<string>WB5752S5M6.com.B5xPo.9xnOT</string>
<key>com.apple.developer.ClassKit-environment</key>
<array><string>production</string></array>
```

证书 team `WB5752S5M6`, bundle `com.B5xPo.9xnOT`,production 签名 OK。

---

## 2. ⚠️ 真机截屏能力受限(诚实交代)

**想要做的事**: idevicescreenshot 拿真机视觉截屏 → 用 desktop ↔ iPad 像素对比闭环
**实际限制**:
- `idevicescreenshot`: 需挂 iOS 27.0 的 Developer Disk Image(DDI)
- iOS 27.0 DDI: **Apple 未公开发布**(公开 DDI 截止 iOS 17.x)
- `idevicedebug run com.B5xPo.9xnOT`: 同样需要 DDI 才能起 debugserver
- iOS 27 真机截屏在 Windows 上**没有公开可用的脚本路径**

**绕路尝试过的工具**(全部失败):
- ❌ Sideloadly daemon (本地 daemon 没有 HTTP API 端口响应)
- ❌ idevicescreenshot (需 DDI)
- ❌ idevicedebug run (需 DDI)
- ❌ pymobiledevice3 pip install (lzfse 编译失败)

**我能从 Windows 侧做的最大化**:
- ✅ 装 .ipa(已成功)
- ✅ 验证 App 已注册在设备(已成功)
- ✅ 读 syslog(普通 release build 也有进程日志)
- ❌ 启动 App(需要 debugserver/DDI)
- ❌ 截屏(需要 DDI 或 Xcode)

---

## 3. 待你做的事(2 分钟)

**v0.5 .ipa 已就绪在 iPad 主屏上**。请:

1. **打开 iPad**,在主屏找 "Buckshot Roulette" 图标点开
2. **iOS 可能弹"未受信任的开发者"**:
   - 设置 → 通用 → VPN 与设备管理(或描述文件)→ 找到开发者 `WB5752S5M6` → 信任
3. **回主屏再点 Buckshot Roulette**
4. **肉眼验证**(主菜单):
   - 显示 "BUCKSHOT ROULETTE / A COMPUTER GAME BY MIKE KLUBNIKA / START"?
   - 左下 shotgun 装饰模型是否在?
   - 整体暗色 CRT 滤镜是否在?
5. **截屏**(电源+音量上)→ 把 `IMG_XXXX.PNG` 拷到电脑:
   - `G:\BDDL\Buckshot_decompiled\dist\v0.5\ipad_screenshots\ip_menu.png`

---

## 4. 收到你截屏后我会做的事

用同一套 pixel diff(参考 [dist/v0.4/macos_desktop_visual_acceptance.md](../v0.4/macos_desktop_visual_acceptance.md))做 desktop ↔ iPad 视觉连续性闭环:

```
UI 文字区  diff>50  < 1%   ←  桌面端已 PASS,iPad 应一致
3D mesh  diff>30  ~33%   ←  浮点抖动在真机 GPU 上可能略不同
全屏 mean RGB 差    < 2%  ←  总体亮度一致
```

如果 iPad 截屏出现 desktop 验证里没有的偏差(贴图错误 / 错位 / 黑屏 / 启动崩溃),这会触发反编译自愈 loop —— 我从 iPad syslog 反查 PCK/资源缺失,push 修复,CI 重 build,再装。

---

## 5. 三大交付最终状态

| 交付 | 状态 |
| --- | --- |
| (1) 1:1 纹理/视觉复刻 | ✅ byte-level PASS (desktop 已验证) + 真机已装 v0.5,**待肉眼** |
| (2) 自动反编译修复 | ✅ ios.yml 7 phase + pck_visual 自愈 loop |
| (3) 全自动执行 | ✅ macos-14 自动跑通 build #30159083423 |

唯一缺的就是**你肉眼确认 + 截屏发我**做最后一环闭环。在收到你截屏反馈前,我不能声称"100% 完成"。