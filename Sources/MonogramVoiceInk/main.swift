import Foundation
import AppKit

// Batch 2: Core-Graphics-Rendering aufs Display + LED + Tasten lesen.
guard let dev = MonogramDevice.autodetect() else {
    print("Kein Monogram-Port gefunden. Gerät angeschlossen und Monogram-Dienst beendet?")
    exit(1)
}
print("Verbunden mit \(dev.path). Strg+C beendet.")

dev.onButton = { ev, _ in
    print("Slot \(ev.slot) · Taste \(ev.button) · \(ev.pressed ? "↓ gedrückt" : "↑ losgelassen")")
}
dev.open()

// Kurz warten, bis der Port offen ist, dann Display + LED setzen.
DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
    dev.setBrightness()
    dev.writeDisplay(Screens.ready(mode: "Default"))
    dev.setLED(0, 40, 70)
    print("READY-Screen + LED geschrieben.")
}

RunLoop.main.run()
