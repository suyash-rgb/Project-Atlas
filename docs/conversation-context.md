# Conversation context for follow-up questions

The chat API accepts an optional `conversation_history` array containing up to
eight ordered messages. Each item has a `role` (`user` or `assistant`) and a
`content` string of at most 2,000 characters. The portal builds this history
server-side from completed conversations for the authenticated client and the
current portal session; callers should not use a client-supplied transcript as
the source of truth.

For a request with history, Atlas checks the raw latest message with the security
router before asking the LLM to resolve references. The resolved standalone
question is routed again for the current turn. History is provided to answer
synthesis as context only; report excerpts, verified database results, and
deterministic calculations remain the factual evidence. When the model cannot
resolve a reference unambiguously, it returns a clarification request rather
than guessing.

Contextual requests bypass both response caches so an answer from a different
conversation cannot satisfy a short follow-up. Requests without history retain
the existing cache behavior.
