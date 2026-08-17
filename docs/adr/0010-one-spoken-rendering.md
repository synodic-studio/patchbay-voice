# One rendering, and it is the spoken one

The model is told to write for the ear, so a URL comes back as "go dot synodic dot co slash obsidian" rather than `go.synodic.co/obsidian`. That string is what gets synthesized, what `[turn:said]` logs, and what any transcript shows. There is no second, written-for-the-eye version of the same reply.

It reads oddly on a screen. That is the accepted cost.

## Considered Options

**Generate both, speak one and display the other** — rejected. Podcast Pusher runs this way and the two renderings drift: every downstream consumer has to know which one it is holding, and a fix applied to one silently fails to reach the other. The failure is quiet and shows up late, which is the worst shape a bug can have.

**Normalize text to speech at the TTS boundary instead** — rejected for the same reason in a smaller form. A normalizer is a second rendering that happens to be derived rather than generated, and it still has to be correct about code, paths, refs, and identifiers it was never shown. Asking the model for speech directly puts that judgment where the context is.

This is a voice product. When the two audiences conflict, the ear wins, and everything downstream reads the same string the speaker did.
