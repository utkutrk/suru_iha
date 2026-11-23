"""Taşıyıcı soyutlaması ve simülasyon/saha için asyncio tabanlı UDP taşıyıcı."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

from yazilim.ag.mesaj import AgMesaji, MesajKodlayici


class Tasiyici(ABC):
    """Dronlar arası haberleşme arayüzü (UDP veya sahada telsiz ile değiştirilebilir)."""

    @abstractmethod
    async def baslat(self) -> None:
        """Dinleme ve gönderim soketlerini açar."""

    @abstractmethod
    async def kapat(self) -> None:
        """Soketleri temizce kapatır."""

    @abstractmethod
    def yayinla(self, tip: str, veri: dict[str, Any]) -> None:
        """Mesajı sürüdeki tüm komşulara gönderir."""

    @abstractmethod
    def mesaj_dinleyici_ekle(self, geri_cagrim: Callable[[AgMesaji], None]) -> None:
        """Doğrulanmış mesaj geldiğinde çağrılacak fonksiyonu kaydeder."""


class _UdpProtokol(asyncio.DatagramProtocol):
    def __init__(
        self,
        kodlayici: MesajKodlayici,
        kendi_id: int,
        dinleyiciler: list[Callable[[AgMesaji], None]],
        logger: logging.Logger,
    ) -> None:
        self._kodlayici = kodlayici
        self._kendi_id = kendi_id
        self._dinleyiciler = dinleyiciler
        self._logger = logger

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        mesaj = self._kodlayici.coz(data)
        if mesaj is None:
            self._logger.debug("Geçersiz/bayat/yanlış anahtarlı UDP paketi atıldı: %s", addr)
            return
        if mesaj.gonderen == self._kendi_id:
            return
        for dinleyici in self._dinleyiciler:
            try:
                dinleyici(mesaj)
            except Exception:
                self._logger.exception("Mesaj dinleyici hatası (tip=%s)", mesaj.tip)


class UdpTasiyici(Tasiyici):
    """Eşler arası (peer-to-peer) dağıtık UDP taşıyıcısı."""

    def __init__(
        self,
        iha_id: int,
        tum_iha_idleri: list[int],
        dinleme_adresi: str,
        hedef_adresi: str,
        udp_taban_portu: int,
        kodlayici: MesajKodlayici,
        logger: logging.Logger,
    ) -> None:
        self._iha_id = iha_id
        self._komsu_idleri = [i for i in tum_iha_idleri if i != iha_id]
        self._dinleme_adresi = dinleme_adresi
        self._hedef_adresi = hedef_adresi
        self._taban_port = udp_taban_portu
        self._kodlayici = kodlayici
        self._logger = logger
        self._dinleyiciler: list[Callable[[AgMesaji], None]] = []
        self._transport: asyncio.DatagramTransport | None = None

    def port_hesapla(self, iha_id: int) -> int:
        return self._taban_port + iha_id

    async def baslat(self) -> None:
        dongu = asyncio.get_running_loop()
        kendi_port = self.port_hesapla(self._iha_id)
        protokol = _UdpProtokol(
            self._kodlayici, self._iha_id, self._dinleyiciler, self._logger
        )
        self._transport, _ = await dongu.create_datagram_endpoint(
            lambda: protokol,
            local_addr=(self._dinleme_adresi, kendi_port),
        )
        self._logger.info(
            "UDP taşıyıcı başlatıldı: %s:%d (komşular=%s)",
            self._dinleme_adresi,
            kendi_port,
            self._komsu_idleri,
        )

    async def kapat(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    def yayinla(self, tip: str, veri: dict[str, Any]) -> None:
        if self._transport is None:
            return
        paket = self._kodlayici.paketle(tip=tip, gonderen=self._iha_id, veri=veri)
        for komsu_id in self._komsu_idleri:
            self._transport.sendto(paket, (self._hedef_adresi, self.port_hesapla(komsu_id)))

    def mesaj_dinleyici_ekle(self, geri_cagrim: Callable[[AgMesaji], None]) -> None:
        self._dinleyiciler.append(geri_cagrim)
