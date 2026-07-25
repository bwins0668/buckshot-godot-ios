# iPad 真机侧载指南

**目标**: 把 `dist/v0.5/buckshot_v0.5.ipa` (184MB) 装到你的 iPad (UDID `00008112-001E20A02221A01E`),肉眼验证 Buckshot Roulette 视觉 1:1 复刻。

---

## ✅ v0.5 已自动装上(2026-07-25 22:30 UTC)

我用 `ideviceinstaller` 脚本自动覆盖安装了 v0.5。装后查:

- iPad 上 `com.B5xPo.9xnOT, "1", "Buckshot Roulette"` 已就位
- Bundle metadata 验证完整(application-identifier = `WB5752S5M6.com.B5xPo.9xnOT`)

**装后你需要做的 5 步**:

### 步骤 1: 信任证书(如果 iOS 弹窗)

iOS 启动未签名 App 时会弹"未受信任的开发者":
1. **设置 → 通用 → VPN 与设备管理**(或 **描述文件与设备管理**)
2. 找开发者 `WB5752S5M6` → **信任**
3. 回主屏

### 步骤 2: 启动

点主屏 **Buckshot Roulette** 图标启动

### 步骤 3: 肉眼验收(主菜单)

- ✅/❌ 显示 "BUCKSHOT ROULETTE" 标题?
- ✅/❌ 显示 "A COMPUTER GAME BY MIKE KLUBNIKA" 副标题?
- ✅/❌ 显示 "START" 按钮?
- ✅/❌ 左下 shotgun 装饰模型是否在?
- ✅/❌ 整体暗色 CRT 滤镜?

### 步骤 4: 进游戏(点 START 后)

- ✅/❌ 桌面 / shotgun / shells 渲染正常?
- ✅/❌ HP 数字显示?
- ✅/❌ 拾取 / 射击交互响应?

### 步骤 5: 截屏发我

真机按 **电源 + 音量上**:
- 主菜单 → `IMG_*.PNG` 拷到电脑 → 改名 `ip_menu.png`
- 游戏内 → `IMG_*.PNG` → 改名 `ip_game.png`

放到:
```
G:\BDDL\Buckshot_decompiled\dist\v0.5\ipad_screenshots\
```

---

## 反馈给我

把这三个回答发我:
1. ✅/❌ 启动是否黑屏?
2. ✅/❌ 主菜单 UI 是否和原游戏一致?
3. ✅/❌ 进入游戏后视觉是否一致?

收到截屏后,我用同一套 pixel diff 做 desktop ↔ iPad 视觉闭环。

---

## 我已做的(in case 你想审计)

```bash
# 我用的实际命令
cd "C:/Tools/libimobiledevice"
./ideviceinstaller.exe -u 00008112-001E20A02221A01E -i \
    "G:/BDDL/Buckshot_decompiled/dist/v0.5/buckshot_v0.5.ipa"
# 输出: Install: Complete
```

`libimobiledevice-win32` v1.2.1 是 Windows 上的开源 iTunes 等价物,
4.3MB,不依赖 iTunes,纯 CLI。