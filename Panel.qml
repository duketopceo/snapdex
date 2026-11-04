import QtQuick 6.11
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons as Commons
import qs.Ui

// Snapdex: camera glyph + badge (inbox count only: unprocessed screenshots)
// and a panel with the last 12 captioned screenshots read from the Library
// (snapdex-ctl returns each item's absolute path), caption search, "Process now" and the
// auto-processing toggle. All state and work lives in bin/snapdex-ctl; the
// systemd user path unit does the real watching, so this only shows status.
//
// Theme access goes through Commons.* with try/catch fallbacks so the same
// file loads on the Omarchy 4.x shell and on 4.5 (where a bare `Color.`
// no longer resolves). No hex colours: fallbacks come from the Qt palette.
Panel {
  id: root
  moduleName: "io.github.duketopceo.snapdex"
  ipcTarget: "io.github.duketopceo.snapdex"

  property bool statusKnown: false
  property int pending: 0
  property int indexedCount: 0
  property bool autoEnabled: false
  property bool autoActive: false
  property var lastRun: null          // epoch seconds
  property var items: []
  property string query: ""
  property string lastError: ""
  property bool busy: false
  property string lastAction: ""
  property string logTail: ""

  SystemPalette { id: sysPal }

  function themed(name, fallback) {
    try {
      var v = Commons.Color[name]
      return (v !== undefined && v !== null) ? v : fallback
    } catch (e) { return fallback }
  }
  function sp(n) {
    try { return Commons.Style.space(n) } catch (e) { return n }
  }
  function fontPx(key, fallback) {
    try {
      var v = Commons.Style.font[key]
      return (typeof v === "number" && v > 0) ? v : fallback
    } catch (e) { return fallback }
  }
  function radius() {
    try { return Commons.Style.cornerRadius } catch (e) { return 0 }
  }

  readonly property color foreground: bar ? bar.foreground : themed("foreground", sysPal.windowText)
  readonly property color dim: Qt.darker(foreground, 1.5)
  readonly property color accent: themed("accent", sysPal.highlight)
  readonly property color urgent: themed("urgent", sysPal.link)
  readonly property color backdrop: themed("background", sysPal.window)
  readonly property string fontFamily: bar ? bar.fontFamily : "monospace"
  readonly property int captionPx: fontPx("caption", 11)
  readonly property int subtitlePx: fontPx("subtitle", 13)
  readonly property int iconLargePx: fontPx("iconLarge", 18)
  readonly property string pluginRoot: {
    var p = Qt.resolvedUrl(".").toString()
    if (p.indexOf("file://") === 0) p = p.substring(7)
    if (p.length > 1 && p.charAt(p.length - 1) === "/") p = p.substring(0, p.length - 1)
    return p
  }
  readonly property string py: "/usr/bin/python3"
  readonly property string ctl: pluginRoot + "/bin/snapdex-ctl"
  readonly property var procEnv: ({
    "PATH": "/usr/bin:/bin",
    "LANG": "C.UTF-8",
    "HOME": Quickshell.env("HOME"),
    "XDG_RUNTIME_DIR": Quickshell.env("XDG_RUNTIME_DIR") || ""
  })

  function fillFor(c, alpha) { return Qt.rgba(c.r, c.g, c.b, alpha) }

  function fmtAgo(epoch) {
    if (epoch === null || epoch === undefined) return "never"
    var s = Math.max(0, Math.floor(Date.now() / 1000 - epoch))
    if (s < 90) return "just now"
    if (s < 5400) return Math.round(s / 60) + "m ago"
    if (s < 129600) return Math.round(s / 3600) + "h ago"
    return Math.round(s / 86400) + "d ago"
  }

  function apply(data) {
    if (!data || typeof data !== "object") return
    if (typeof data.pending === "number") { root.pending = data.pending; root.statusKnown = true }
    if (data.auto) { root.autoEnabled = data.auto.enabled === true; root.autoActive = data.auto.active === true }
    root.lastRun = (typeof data.last_run === "number") ? data.last_run : null
    if (typeof data.indexed === "number") root.indexedCount = data.indexed
    if (Array.isArray(data.items)) root.items = data.items
    root.lastError = (typeof data.error === "string") ? data.error : ""
    if (typeof data.log === "string") root.logTail = data.log
  }

  function groupKill(proc) {
    if (proc.running) {
      var pid = proc.pid
      if (pid > 0) Quickshell.execDetached(["/usr/bin/kill", "-KILL", "--", "-" + pid.toString()])
      proc.signal(9)
    }
  }

  function refreshStatus() {
    if (statusProc.running || panelProc.running) return
    statusProc.running = true
    statusDeadline.restart()
  }
  function refreshPanel() {
    if (panelProc.running) return
    panelProc.command = [root.py, root.ctl, "panel", root.query]
    panelProc.running = true
    panelDeadline.restart()
  }
  function control(argv, label, longRun) {
    if (ctrlProc.running) return
    root.busy = true
    root.lastAction = label
    root.lastError = ""
    ctrlProc.command = [root.py, root.ctl].concat(argv)
    ctrlProc.running = true
    ctrlDeadline.interval = longRun ? 1200000 : 20000
    ctrlDeadline.restart()
  }

  function openShot(path) { Quickshell.execDetached(["xdg-open", path]) }
  function copyPath(path) {
    Quickshell.execDetached(["wl-copy", path])
    root.lastAction = "copied"
    copiedTimer.restart()
  }

  onOpenedChanged: if (opened) { root.refreshPanel() }
  onQueryChanged: queryDebounce.restart()

  Process {
    id: statusProc
    command: [root.py, root.ctl, "status"]
    clearEnvironment: true
    environment: root.procEnv
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        statusDeadline.stop()
        try {
          if (!text || text.trim().length === 0 || text.length > 200000) return
          root.apply(JSON.parse(text))
        } catch (e) {}
      }
    }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {} }
    onExited: statusDeadline.stop()
  }

  Process {
    id: panelProc
    clearEnvironment: true
    environment: root.procEnv
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        panelDeadline.stop()
        try {
          if (!text || text.trim().length === 0 || text.length > 400000) return
          root.apply(JSON.parse(text))
        } catch (e) {}
      }
    }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {} }
    onExited: panelDeadline.stop()
  }

  Process {
    id: ctrlProc
    clearEnvironment: true
    environment: root.procEnv
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        ctrlDeadline.stop()
        root.busy = false
        try {
          if (text && text.trim().length > 0 && text.length < 400000) root.apply(JSON.parse(text))
        } catch (e) {}
        root.refreshPanel()
      }
    }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: {} }
    onExited: { ctrlDeadline.stop(); root.busy = false }
  }

  Timer { id: statusDeadline; interval: 15000; onTriggered: root.groupKill(statusProc) }
  Timer { id: panelDeadline;  interval: 15000; onTriggered: root.groupKill(panelProc) }
  Timer { id: ctrlDeadline;   interval: 20000; onTriggered: { root.groupKill(ctrlProc); root.busy = false } }
  Timer { id: statusTimer;    interval: 30000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.refreshStatus() }
  Timer { id: queryDebounce;  interval: 200; onTriggered: if (root.opened) root.refreshPanel() }
  Timer { id: copiedTimer;    interval: 1500; onTriggered: if (root.lastAction === "copied") root.lastAction = "" }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "0"
    tooltipText: "Snapdex · " + (root.pending > 0 ? root.pending + " unprocessed" : "all indexed")
                 + (root.autoEnabled ? " · auto on" : "")
    active: root.autoEnabled
    activeColor: root.accent
    foreground: root.pending > 0 ? root.accent : root.dim
    onPressed: function (b) { root.toggle() }

    Rectangle {
      id: badge
      visible: root.pending > 0
      z: 5
      anchors.right: parent.right
      anchors.top: parent.top
      anchors.rightMargin: -root.sp(1)
      anchors.topMargin: -root.sp(1)
      height: root.sp(11)
      width: Math.max(height, badgeText.implicitWidth + root.sp(4))
      radius: height / 2
      color: root.accent
      Text {
        id: badgeText
        anchors.centerIn: parent
        text: root.pending > 99 ? "99+" : root.pending.toString()
        textFormat: Text.PlainText
        color: root.backdrop
        font.family: root.fontFamily
        font.pixelSize: root.sp(8)
        font.bold: true
      }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    contentWidth: panel.fittedContentWidth(root.sp(420), 440)
    contentHeight: panel.fittedContentHeight(mainColumn.implicitHeight, 800)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      blocked: search.activeFocus
      onCloseRequested: root.close()
      onTextKey: function (t, m) { if (t === "/") search.forceActiveFocus() }

      Column {
        id: mainColumn
        width: parent.width
        spacing: root.sp(10)

        // ---- header ----
        Row {
          width: parent.width
          spacing: root.sp(10)

          Rectangle {
            id: iconTile
            width: root.sp(34); height: root.sp(34)
            radius: root.radius()
            color: root.fillFor(root.accent, 0.12)
            anchors.verticalCenter: parent.verticalCenter
            Text {
              anchors.centerIn: parent
              text: "0"; textFormat: Text.PlainText
              color: root.pending > 0 ? root.accent : root.dim
              font.family: root.fontFamily; font.pixelSize: root.iconLargePx
            }
          }

          Column {
            width: parent.width - iconTile.width - autoRow.width - parent.spacing * 2
            spacing: root.sp(2)
            anchors.verticalCenter: parent.verticalCenter
            Text {
              text: "SNAPDEX"; textFormat: Text.PlainText
              color: root.foreground
              font.family: root.fontFamily; font.pixelSize: root.subtitlePx; font.bold: true
            }
            Text {
              width: parent.width
              text: root.pending + " pending · " + root.indexedCount + " indexed · " + root.fmtAgo(root.lastRun)
              textFormat: Text.PlainText
              color: root.dim
              font.family: root.fontFamily; font.pixelSize: root.captionPx
              elide: Text.ElideRight
            }
          }

          Row {
            id: autoRow
            spacing: root.sp(6)
            anchors.verticalCenter: parent.verticalCenter
            Text {
              anchors.verticalCenter: parent.verticalCenter
              text: "auto"; textFormat: Text.PlainText
              color: root.autoEnabled ? root.accent : root.dim
              font.family: root.fontFamily; font.pixelSize: root.captionPx; font.bold: true
            }
            ToggleSwitch {
              anchors.verticalCenter: parent.verticalCenter
              checked: root.autoEnabled
              busy: root.busy && root.lastAction.indexOf("auto") === 0
              onToggled: root.control(["auto", root.autoEnabled ? "off" : "on"],
                                      "auto " + (root.autoEnabled ? "off" : "on"), false)
            }
          }
        }

        // ---- search ----
        Rectangle {
          width: parent.width
          height: root.sp(30)
          radius: root.radius()
          color: root.fillFor(root.foreground, 0.05)
          border.color: root.fillFor(search.activeFocus ? root.accent : root.foreground, search.activeFocus ? 0.6 : 0.2)

          FilterInput {
            id: search
            anchors.fill: parent
            anchors.leftMargin: root.sp(10)
            anchors.rightMargin: root.sp(10)
            verticalAlignment: TextInput.AlignVCenter
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: root.subtitlePx
            keyHandler: keyCatcher
            focus: false
            onTextChanged: root.query = text
            Keys.onEscapePressed: function (event) {
              if (search.text.length > 0) search.text = ""
              else root.close()
              event.accepted = true
            }
          }
          Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: root.sp(10)
            visible: search.text.length === 0 && !search.activeFocus
            text: "Search captions  (press /)"
            textFormat: Text.PlainText
            color: root.dim
            font.family: root.fontFamily; font.pixelSize: root.captionPx
          }
        }

        // ---- thumbnails ----
        PanelSectionHeader {
          text: root.query.trim() !== "" ? "RESULTS" : "RECENT"
          foreground: root.foreground; fontFamily: root.fontFamily
        }

        Grid {
          id: grid
          width: parent.width
          columns: 3
          spacing: root.sp(8)
          readonly property real cellW: (width - spacing * (columns - 1)) / columns

          Repeater {
            model: root.items.slice(0, 12)
            delegate: Item {
              width: grid.cellW
              height: grid.cellW * 0.62 + root.sp(30)

              Rectangle {
                id: thumbFrame
                width: parent.width
                height: grid.cellW * 0.62
                radius: root.radius()
                color: root.fillFor(root.foreground, 0.06)
                border.color: root.fillFor(root.foreground, thumbMouse.containsMouse ? 0.5 : 0.18)
                clip: true
                Image {
                  anchors.fill: parent
                  source: "file://" + modelData.path
                  asynchronous: true
                  cache: false
                  fillMode: Image.PreserveAspectCrop
                  sourceSize.width: 360
                  sourceSize.height: 240
                }
                MouseArea {
                  id: thumbMouse
                  anchors.fill: parent
                  hoverEnabled: true
                  acceptedButtons: Qt.LeftButton | Qt.RightButton
                  cursorShape: Qt.PointingHandCursor
                  onClicked: function (mouse) {
                    if (mouse.button === Qt.RightButton) root.copyPath(modelData.path)
                    else root.openShot(modelData.path)
                  }
                }
              }
              Text {
                anchors.top: thumbFrame.bottom
                anchors.topMargin: root.sp(3)
                width: parent.width
                text: modelData.caption
                textFormat: Text.PlainText
                color: root.foreground
                font.family: root.fontFamily; font.pixelSize: root.captionPx
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
              }
            }
          }
        }

        Text {
          width: parent.width
          visible: root.items.length === 0
          text: root.query.trim() !== "" ? "No captions match." : "Nothing indexed yet."
          textFormat: Text.PlainText
          color: root.dim
          horizontalAlignment: Text.AlignHCenter
          font.family: root.fontFamily; font.pixelSize: root.captionPx
        }

        Text {
          width: parent.width
          text: root.lastAction === "copied" ? "Path copied." : "Click opens · right-click copies the path"
          textFormat: Text.PlainText
          color: root.lastAction === "copied" ? root.accent : root.dim
          horizontalAlignment: Text.AlignHCenter
          font.family: root.fontFamily; font.pixelSize: root.captionPx
        }

        // ---- process now ----
        Rectangle {
          width: parent.width
          height: root.sp(32)
          radius: root.radius()
          color: procMouse.containsMouse ? root.fillFor(root.accent, 0.14) : root.fillFor(root.accent, 0.07)
          border.color: root.fillFor(root.accent, 0.4)
          opacity: (root.busy || root.pending === 0) ? 0.5 : 1.0
          Text {
            anchors.centerIn: parent
            text: root.busy && root.lastAction === "process"
                  ? "captioning… (paid model calls)"
                  : "Process now · " + root.pending + " pending"
            textFormat: Text.PlainText
            color: root.accent
            font.family: root.fontFamily; font.pixelSize: root.captionPx; font.bold: true
          }
          MouseArea {
            id: procMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            enabled: !root.busy && root.pending > 0
            onClicked: root.control(["process"], "process", true)
          }
        }

        Text {
          width: parent.width
          visible: root.autoEnabled
          text: "Auto: only shots taken since you enabled it are captioned, max 10 per run."
          textFormat: Text.PlainText
          color: root.dim
          wrapMode: Text.WordWrap
          font.family: root.fontFamily; font.pixelSize: root.captionPx
        }

        Text {
          width: parent.width
          visible: root.lastError !== ""
          text: "! " + root.lastError
          textFormat: Text.PlainText
          color: root.urgent
          wrapMode: Text.WordWrap
          font.family: root.fontFamily; font.pixelSize: root.captionPx
        }
      }
    }
  }
}
