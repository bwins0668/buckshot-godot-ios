# iPad 真机侧载指南

**目标**: 把 `dist/v0.5/buckshot_v0.5.ipa` (184MB) 装到你的 iPad (UDID `00008112-001E20A02221A01E`),肉眼验证 Buckshot Roulette 视觉 1:1 复刻。

---

## 前置清单

| 项 | 值 |
| --- | --- |
| iPad UDID | `00008112-001E20A02221A01E` |
| 证书 .zip | `C:\Users\lvgua\Desktop\iPad证书.zip` |
| 证书密码 | `1` |
| Apple ID 团队 | `WB5752S5M6` |
| Bundle ID | `com.B5xPo.9xnOT` |
| .ipa 路径 | `G:\BDDL\Buckshot_decompiled\dist\v0.5\buckshot_v0.5.ipa` |
| .ipa 大小 | 184 MB |
| .ipa md5 | `12c0cb364c5a3f9fd3a8603cb5648fac` |
| 工具 | **Sideloadly** ([sideloadly.io](https://sideloadly.io)) — Windows 客户端 |

> 注: Sideloadly 是 Windows 上免费的 IPA 侧载工具,不需要 Mac。它会用你 .zip 里的 p12 私钥 + mobileprovision 给 .ipa 重签,然后推到 iPad。

---

## 步骤(预计 3-5 分钟)

### 1. 解压证书 .zip

```bash
# 在任意目录解压 C:\Users\lvgua\Desktop\iPad证书.zip
# 密码 = 1
# 解出三个文件(实际可能命名略有不同):
#   *.p12 (私钥)
#   *.mobileprovision (描述文件)
#   (可能还有一份 .cer 公钥)
```

确认里面有:
- 一个 `.p12` 文件
- 一个 `.mobileprovision` 文件

### 2. 安装并启动 Sideloadly

- 从 https://sideloadly.io 下载 Windows 版
- 安装,首次启动会要求输入 Apple ID(**建议用一个临时 Apple ID**,不要用主账号,侧载过的设备会被 Apple 标记 7 天内不能再装这个 App)
- 启动 Sideloadly

### 3. 侧载 .ipa

1. Sideloadly 主界面:
   - **iDevice**: 用 USB-C 线连上 iPad,确保 iPad 已信任此电脑。Sideloadly 应自动检测到 UDID `00008112-001E20A02221A01E`
   - **IPA File**: 点浏览,选 `G:\BDDL\Buckshot_decompiled\dist\v0.5\buckshot_v0.5.ipa`
2. 点右下角 **Start**
3. 弹出提示输入 .p12 密码:输入 `1`
4. 等待进度条走完(预计 30-90 秒),进度条完成会提示 "Installation Complete"

### 4. iPad 上信任证书

1. 在 iPad 上 **设置 → 通用 → VPN 与设备管理**(或 **描述文件与设备管理**)
2. 找到刚装的 "Buckshot Roulette"(开发者: `WB5752S5M6`)
3. 点 **信任**(`WB5752S5M6`)
4. 回到桌面启动 "Buckshot Roulette"

### 5. 验收

启动后:
1. **主菜单是否显示 "BUCKSHOT ROULETTE / A COMPUTER GAME BY MIKE KLUBNIKA / START"** — 桌面验证已 1:1,真机应一致
2. **点 START 进入游戏后**:
   - 桌面 / shotgun / shells 是否正确
   - 左侧 HP 数字是否显示
   - 拾取 / 射击交互是否响应
3. **截屏**(真机按电源+音量上):
   - 主菜单一张 (`ip_menu.png`)
   - 进游戏桌面上方一张 (`ip_game.png`)

---

## 完成后反馈给我

把这三个回答发给我:

1. ✅ / ❌ — 启动是否黑屏?(如黑屏,Godot 4.1.1 真机也可能,但通常真机 OK)
2. ✅ / ❌ — 主菜单 UI 是否和原游戏一致?
3. ✅ / ❌ — 进入游戏后视觉是否一致?

如果有截屏,把 `ip_menu.png` / `ip_game.png` 放到 `G:\BDDL\Buckshot_decompiled\dist\v0.5\ipad_screenshots\` 下,我做 desktop ↔ iPad 像素对比,完成视觉 1:1 闭环。

---

## 如果 Sideloadly 报错

| 错误 | 原因 / 解法 |
| --- | --- |
| "Failed to connect to device" | iPad 没解锁 / 没信任此电脑 |
| "Invalid .p12 password" | 密码不是 `1`,看 .zip 里的 .txt 是否写了别的 |
| "Application verification failed" | 证书过期 / UDID 不匹配。检查 `*.mobileprovision` 是否包含 iPad 的 UDID |
| "Apple ID locked" | 临时 Apple ID 被风控,换一个 |

---

## 如果你不想用 Sideloadly

备选方案:
- **AltStore**: Windows 上用 AltServer + AltStore,流程差不多,但需要 AltStore 在 iPad 上保持一周一次刷新才能继续用
- **直接装 7 天内有效的 IPA**: 任何 iOS 设备临时签名 IPA 都受 7 天限制;7 天后要么重签要么重装

---

**核心结论**: .ipa 是好的(desktop 视觉对比已 PASS),你只需在 iPad 上装一次,肉眼确认就能完成视觉 1:1 复刻的最后一环。