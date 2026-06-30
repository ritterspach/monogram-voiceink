import Foundation
import ORSSerial

/// Überwacht das Monogram-Gerät und hält Verbindung + Controller am Leben.
///
/// Verbindet automatisch, sobald das Gerät auftaucht, und baut bei Verlust sauber
/// ab, damit der nächste Abgleich neu verbindet (Hotplug, Schlaf/Aufwachen,
/// Gerät beim Start noch nicht angesteckt). Dadurch beendet sich die App nie
/// wegen eines fehlenden Geräts – essenziell für den unbeaufsichtigten
/// Hintergrundbetrieb.
final class Supervisor {
    private let manager = ORSSerialPortManager.shared()   // am Leben halten → Portliste aktualisiert sich
    private var dev: MonogramDevice?
    private var controller: Controller?
    private var pollTimer: DispatchSourceTimer?

    func start() {
        reconcile()                                       // sofort versuchen
        let t = DispatchSource.makeTimerSource(queue: .main)
        t.schedule(deadline: .now() + 1.5, repeating: 1.5) // danach regelmäßig abgleichen
        t.setEventHandler { [weak self] in self?.reconcile() }
        t.resume()
        pollTimer = t
    }

    /// Pfad des aktuell angesteckten Monogram-Ports (oder nil).
    private func currentPortPath() -> String? {
        manager.availablePorts.map { $0.path }.first { $0.contains("usbmodem") }
    }

    /// Gleicht Soll (Gerät angesteckt?) und Ist (verbunden?) ab.
    private func reconcile() {
        let path = currentPortPath()
        if let dev {
            if path == nil || path != dev.path {          // unser Port ist weg/anders → abbauen
                Log.device.notice("Monogram entfernt – Verbindung wird abgebaut.")
                teardown()
            }
        } else if let path {
            connect(path)
        }
    }

    private func connect(_ path: String) {
        guard let d = MonogramDevice(path: path) else {
            Log.device.error("Port \(path, privacy: .public) ließ sich nicht öffnen.")
            return
        }
        d.onRemoved = { [weak self] in
            DispatchQueue.main.async { self?.teardown() }
        }
        d.open()
        let c = Controller(dev: d)
        c.start()
        dev = d
        controller = c
        Log.device.notice("Verbunden mit \(path, privacy: .public).")
    }

    private func teardown() {
        controller?.stop()
        dev?.close()
        controller = nil
        dev = nil
    }
}
