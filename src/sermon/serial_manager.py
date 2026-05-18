from dataclasses import dataclass

import serial
import serial.tools.list_ports


@dataclass
class SerialConfig:
    port: str = ""
    baudrate: int = 115200
    bytesize: int = serial.EIGHTBITS
    parity: str = serial.PARITY_NONE
    stopbits: float = serial.STOPBITS_ONE
    timeout: float = 0.05


class SerialError(Exception):
    pass


class SerialManager:
    def __init__(self) -> None:
        self._serial: serial.Serial | None = None
        self.config = SerialConfig()

    @staticmethod
    def list_ports() -> list[dict]:
        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append(
                {
                    "device": p.device,
                    "description": p.description,
                }
            )
        return ports

    def connect(self, config: SerialConfig | None = None) -> None:
        if config is not None:
            self.config = config
        try:
            self._serial = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                bytesize=self.config.bytesize,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                timeout=self.config.timeout,
            )
        except serial.SerialException as e:
            raise SerialError(str(e)) from e

    def disconnect(self) -> None:
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except serial.SerialException:
                pass
        self._serial = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def read(self, size: int = 1024) -> bytes:
        if not self.is_connected:
            return b""
        try:
            return self._serial.read(size)
        except serial.SerialException:
            self.disconnect()
            return b""

    def write(self, data: bytes) -> None:
        if not self.is_connected:
            raise SerialError("Not connected")
        try:
            self._serial.write(data)
        except serial.SerialException as e:
            raise SerialError(str(e)) from e
