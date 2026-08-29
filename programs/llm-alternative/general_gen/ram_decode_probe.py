"""Temporary M0 probe for the fixed-address control decoder."""

from .common import (
    CMD_RECV,
    EVENT_SEND,
    MEM_SIZE,
    RING_RECV,
    RING_SEND,
    STASH_RECV,
    STASH_SEND,
    BackpackLoop,
    IfSign,
    Ops,
    Seq,
    While,
    lit,
    ram_decode_address,
    ram_event,
    write_generated_room,
)


def generate() -> None:
    boot = Seq(
        Ops(lit(MEM_SIZE) + "b"),
        BackpackLoop(Ops(CMD_RECV + "." * 500 + RING_SEND)),
        Ops("0" + ram_event(0)),
    )
    # payload -> stash, op -> discard, decode address, report it, drain payload.
    service = Seq(
        Ops(CMD_RECV + "." * 250 + STASH_SEND),
        Ops(CMD_RECV),
        ram_decode_address(),
        Ops(ram_event(0)),
        Ops("." * 250 + STASH_RECV),
    )
    write_generated_room(
        "llm-alt-general-ram-decode-probe",
        Seq(IfSign("0", Ops(RING_RECV), Ops("."), Ops(".")), boot, While("1", service)),
        {
            "control": CMD_RECV,
            "ring_in": RING_RECV,
            "ring_out": RING_SEND,
            "event": EVENT_SEND,
            "stash_in": STASH_RECV,
            "stash_out": STASH_SEND,
        },
        (("control", "ring_in", "stash_in"), ("ring_out", "event", "stash_out")),
    )
