# Demo UI Style

Use this reference whenever generating or updating the visible Meishe ShortVideo demo entry UI. The goal is to keep generated demos consistent with the provided `home.jpg`, `empty.jpg`, and `project.jpg` references.

## Home

Additional responsive constraints:

- The home screen must fit within one viewport on common phone sizes. Do not let the title, banner, panel, or four action rows extend below the bottom safe area.
- Keep visible bottom whitespace of about 5%-8% of screen height when possible.
- Prefer percentage/flex/weight-based sizing where the target framework supports it. Use screen-height based values for banner height and vertical spacing, with sensible min/max clamps, so different devices keep the same visual proportions.
- Keep title, hint, panel title, row height, and vertical gaps compact enough for the whole page to fit. Prefer title size around 28-32 logical pixels/sp, action row height around 46-52 logical pixels, and row gaps around 8-12 logical pixels.
- Use the bundled custom function icons, not platform default icons or text symbols: `meishe_icon_capture`, `meishe_icon_dual_capture`, `meishe_icon_edit`, and `meishe_icon_draft`. Keep icon size compact, about 24 logical pixels, with the Chinese label and a trailing chevron.

- Use a dark full-screen background close to `#101317` / `#171d26`.
- Show the title `素材上新` near the top-left in large bold white text.
- Show the fixed banner image from `assets/demo-ui/meishe_home_banner.jpg` below the title. It is decoration only and must not have a click handler.
- Show a rounded dark panel containing:
  - `请选择所需的功能`
  - `功能列表`
  - four action rows: `拍摄`, `合拍`, `编辑`, `草稿`
- Keep the action rows rounded, grey, and full width inside the panel. Each row must use the matching bundled custom icon, the label in Chinese, and a trailing chevron.
- Do not generate footer text such as `拍动 v2.0.0`, `用户协议`, `隐私协议`, or any similar legal/product footer.

## Home Loading

- When the home page is entered, automatically prepare required SDK resources: configure server values if that platform wrapper exposes server configuration, then download prefabricated material/assets.
- While preparation is running, show a loading state over or inside the home page and disable the four action rows.
- If preparation succeeds, hide loading and allow the actions.
- If preparation fails or times out, keep the home visible, hide the blocking loading overlay, show a concise warning message, and expose a retry action. Do not keep the user blocked in an infinite loading state.
- 原生 iOS 的服务器配置和预制素材准备必须异步、单飞且非阻塞；网络失败或超时只更新提示，不得阻塞拍摄、合拍、编辑和草稿入口。
- After a timeout or failed material preparation, allow the four action rows to be tapped. The official SDK can continue or retry its own resource preparation when entering capture/edit/dual-capture flows, and the demo must not be unusable because proactive preparation failed.
- The SDK exposes success/fail callbacks rather than reliable percentage progress, so do not render fake percentage progress.

## Drafts

- Use a dark full-screen background close to `#101010`.
- Use the page title `本地草稿箱` centered in the top bar.
- Provide a back affordance on the left side of the top bar.
- Empty state: center the text `没有草稿啦！` vertically in the content area.
- Keep draft typography smaller than earlier templates: title about 24-26, notice about 18-20, empty text about 22-24, row title about 20-22, thumbnail about 88-100, and play overlay about 42-48.
- Non-empty state:
  - Show `温馨提示： 卸载应用后，草稿也会被删除` near the top.
  - Render draft rows with a square rounded thumbnail on the left, a play overlay icon on the thumbnail, and the draft title on the right.
  - Prefer the draft description when it is meaningful; otherwise use `草稿-MMDD` derived from available time fields or the current date as a fallback.
  - Open/re-edit the draft when the row or thumbnail is tapped.
  - If delete is supported in the generated UI, expose it through a long-press flow with a confirmation prompt so the default visual state matches the reference image.

## Publish / Next Step

- When the user taps Next from SDK edit, capture, or dual-capture flows and the wrapper receives the publish event, show a generated publish/next-step page in the same dark visual system as the draft screen.
- Do not use a light form page or English labels. Use a dark full-screen background, a left back affordance, centered Chinese title such as `作品发布`, compact white text, and a project row styled like the non-empty draft row in `project.jpg`.
- The project row should show the current project cover/thumbnail when available, a play overlay, and a title based on meaningful draft/project info with `草稿-MMDD` fallback.
- Preserve the generated page functionality: save draft, export/compile, show compile progress/status, and return/back. Style these controls as compact dark buttons or bottom actions, not large bright cards.
- Every iOS route that renders the draft-description input must dismiss the keyboard when the user taps outside the input and when the surrounding scroll view is dragged. The keyboard must resize or inset the scrollable area so the input, status, save-draft, and export controls remain reachable; do not rely on an Apple keyboard dismiss key being present.

## Platform Notes

- 原生 iOS 生成模板必须自动复制并引用 bundled banner 和图标资源。
- Native iOS generates UIKit home, drafts, and publish view controllers with this same visual system. The handoff must still require Xcode target membership/resource membership, entry navigation to `MeisheShortVideoHomeViewController`, material preparation verification, and SDK-version-specific delegate checks.
