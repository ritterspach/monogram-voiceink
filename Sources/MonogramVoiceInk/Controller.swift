import Foundation
import CoreGraphics
import QuartzCore

/// Verbindet Tasten + Display + LED + VoiceInk.
/// Taste 1: AUSSCHLIESSLICH Aufnahme – kurz tippen = an/aus (Toggle), halten = Push-to-Talk.
///          Nimmt im aktuell GEWÄHLTEN Modus auf (per-Modus-Kürzel), sonst über den
///          globalen Aufnahme-Hotkey. Gestoppt wird immer über den globalen Hotkey.
/// Taste 2: AUSSCHLIESSLICH Modus auswählen – Anzeige auf dem Geräte-Display,
///          keine Aufnahme. VoiceInks UI wird nicht angefasst; Taste 1 nimmt im
///          gewählten Modus über dessen eigenes Kürzel auf.
final class Controller {
    private let dev: MonogramDevice
    private var modes: [VIMode]
    private let toggle: (CGKeyCode, CGEventFlags)?
    private var selected = 0

    private var recording = false
    private var latched = false
    private var pressTime = 0.0
    private var downStopped = false
    private var recStart = 0.0
    private var lastSec = -1
    private var overlayUntil = 0.0
    private var didStartup = false

    private let tapMax = 0.35
    private var timer: DispatchSourceTimer?

    init(dev: MonogramDevice) {
        self.dev = dev
        self.modes = VoiceInk.modes()
        self.toggle = VoiceInk.recordingToggle()
        if let active = VoiceInk.activeModeId(),
           let idx = modes.firstIndex(where: { $0.id == active }) {
            selected = idx
        }
    }

    private var modeName: String { modes.isEmpty ? "—" : modes[selected].name }

    func start() {
        dev.onButton = { [weak self] ev, ts in
            DispatchQueue.main.async { self?.onButton(ev, ts) }
        }
        let t = DispatchSource.makeTimerSource(queue: .main)
        t.schedule(deadline: .now() + 0.08, repeating: 0.08)
        t.setEventHandler { [weak self] in self?.tick() }
        t.resume()
        timer = t

        // Startanzeige erst, wenn der Port wirklich offen ist – sonst gehen die
        // Schreibvorgänge beim Wieder-Anstecken verloren (open() ist asynchron).
        dev.onOpened = { [weak self] in self?.scheduleStartupDraw() }
        if dev.isOpen { scheduleStartupDraw() }

        let withSc = modes.filter { $0.shortcut != nil }.map { $0.name }
        let summary = "Modi: \(modes.map { $0.name }.joined(separator: ", "))  |  mit eigenem Shortcut: \(withSc.isEmpty ? "keine" : withSc.joined(separator: ", "))  |  Aufnahme-Hotkey: \(toggle != nil ? "ok" : "fehlt")"
        Log.app.notice("\(summary, privacy: .public)")
    }

    /// Zeichnet Helligkeit + Idle-Screen einmalig, kurz nachdem der Port offen ist
    /// (kleine Settle-Zeit, da das Gerät beim Enumerieren einen Moment braucht).
    private func scheduleStartupDraw() {
        guard !didStartup else { return }
        didStartup = true
        // Das Gerät hat keinen Bereitschafts-Indikator und sendet nichts von sich aus;
        // nach einem Replug braucht es unterschiedlich lange, bis es Befehle annimmt.
        // Helligkeit daher mehrfach über die ersten Sekunden neu setzen – flimmerfrei,
        // da reines set_brightness ohne Neuaufbau. So bleibt die Beleuchtung auch dann
        // an, wenn das Gerät erst spät bereit ist (sonst bliebe sie dauerhaft aus).
        for delay in [0.3, 0.8, 1.5, 2.5, 4.0, 6.0] {
            DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
                guard let self, !self.recording else { return }
                self.dev.setBrightness()
            }
        }
        // Idle-Screen seltener neu zeichnen (Neuaufbau vermeiden), abgebrochen falls
        // inzwischen aufgenommen wird oder ein Modus-Overlay aktiv ist.
        for delay in [0.5, 1.5, 3.0] {
            DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
                guard let self, !self.recording, self.overlayUntil == 0 else { return }
                self.showIdle()
            }
        }
    }

    /// Baut Timer und Geräte-Callbacks ab (z. B. wenn das Gerät verschwindet).
    func stop() {
        timer?.cancel()
        timer = nil
        dev.onButton = nil
        dev.onOpened = nil
    }

    private func onButton(_ ev: ButtonEvent, _ ts: Double) {
        guard ev.slot == 0 else { return }
        if ev.button == 1 {
            ev.pressed ? btn1Down(ts) : btn1Up(ts)
        } else if ev.button == 2, ev.pressed {
            nextMode()
        }
    }

    // MARK: - Taste 1: nur Aufnahme

    private func btn1Down(_ ts: Double) {
        pressTime = ts
        if recording && latched {
            stopRec(); downStopped = true
        } else {
            startRec(); downStopped = false
        }
    }

    private func btn1Up(_ ts: Double) {
        if downStopped { downStopped = false; return }
        if ts - pressTime < tapMax {
            latched = true                     // kurzer Tipp -> Aufnahme bleibt an
        } else {
            stopRec()                          // gehalten -> PTT -> stoppen
        }
    }

    private func startRec() {
        guard !recording else { return }
        let modeSc = (selected < modes.count) ? modes[selected].shortcut : nil
        guard let sc = modeSc ?? toggle else { return }   // Modus-Kürzel, sonst globaler Hotkey
        VoiceInk.send(keyCode: sc.0, flags: sc.1)
        recording = true; latched = false
        recStart = CACurrentMediaTime(); lastSec = -1
        dev.setLED(255, 0, 0)
        dev.writeDisplay(Screens.rec(elapsed: 0, mode: modeName))
    }

    private func stopRec() {
        guard recording else { return }
        if let t = toggle { VoiceInk.send(keyCode: t.0, flags: t.1) }   // immer über globalen Toggle stoppen
        recording = false; latched = false
        showIdle()
    }

    // MARK: - Taste 2: nur Modus auswählen (kein Tastendruck)

    private func nextMode() {
        refreshModes()                                   // Modi dynamisch frisch einlesen
        guard !modes.isEmpty else { return }
        selected = (selected + 1) % modes.count
        // Reine Geräte-Auswahl: nur das Display zeigt den Modus, keine VoiceInk-
        // Einstellung wird angefasst. Der Modus wird erst beim Aufnehmen wirksam –
        // Taste 1 sendet das Modus-Kürzel, das in VoiceInk direkt eine Aufnahme in
        // diesem Modus startet (laut Doku: „starts recording directly with this Mode").
        dev.writeDisplay(Screens.mode(modeName))
        overlayUntil = CACurrentMediaTime() + 1.0
    }

    /// Liest VoiceInks Modusliste neu ein und hält die aktuelle Auswahl (per id) fest.
    private func refreshModes() {
        let currentId = (selected < modes.count) ? modes[selected].id : nil
        modes = VoiceInk.modes()
        if let currentId, let idx = modes.firstIndex(where: { $0.id == currentId }) {
            selected = idx
        } else if selected >= modes.count {
            selected = 0
        }
    }

    // MARK: - Anzeige

    private func showIdle() {
        dev.writeDisplay(Screens.ready(mode: modeName))
        dev.setLED(0, 40, 70)
    }

    private func tick() {
        let now = CACurrentMediaTime()
        if now < overlayUntil { return }
        if overlayUntil != 0 {                 // Modusname-Overlay gerade abgelaufen
            overlayUntil = 0; lastSec = -1
            if !recording { showIdle() }
        }
        if recording {
            let pulse = 0.5 * (1 + sin(now * 8))
            dev.setLED(Int(80 + 175 * pulse), 0, 0)         // pulsierendes Rot
            let sec = Int(now - recStart)
            if sec != lastSec {
                lastSec = sec
                dev.writeDisplay(Screens.rec(elapsed: sec, mode: modeName), liveRefresh: true)
            }
        }
    }
}
