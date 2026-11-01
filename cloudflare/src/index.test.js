import assert from "node:assert/strict";
import test from "node:test";
import worker from "./index.js";

const TOKEN = "test-token-with-more-than-24-characters";

function openingRequest(overrides = {}) {
  return {
    kind: "opening",
    language: "it",
    setting: "Un porto in cui le campane suonano sott'acqua.",
    extra: "",
    duration: 60,
    difficulty: "medium",
    party: [{
      name: "Mira",
      species: "Elfa",
      class: "Barda",
      story_ability: "Ispirazione — Usa parole e musica per coinvolgere gli altri.",
    }],
    history: [],
    ...overrides,
  };
}

function adjudicateRequest(overrides = {}) {
  return {
    kind: "adjudicate",
    language: "it",
    setting: "Un porto in cui le campane suonano sott'acqua.",
    extra: "",
    difficulty: "medium",
    party: [{
      name: "Mira",
      species: "Elfa",
      class: "Barda",
      abilities: {
        strength: 8,
        dexterity: 14,
        constitution: 12,
        intelligence: 13,
        wisdom: 10,
        charisma: 15,
      },
      skills: ["performance", "persuasion"],
    }],
    action: "Mira convince il traghettatore a lasciarci passare.",
    history: [],
    ...overrides,
  };
}

function checkRequest(passed, checkOverrides = {}) {
  return {
    kind: "check",
    language: "it",
    setting: "Un porto in cui le campane suonano sott'acqua.",
    extra: "",
    party: [{ name: "Mira", species: "Elfa", class: "Barda", hit_points: 9 }],
    action: "Mira cerca di persuadere il traghettatore.",
    check: {
      actor: "Mira",
      ability: "Carisma",
      score: 15,
      modifier: 4,
      roll: 3,
      total: 7,
      target: 13,
      passed,
      proficient: true,
      ...checkOverrides,
    },
    history: [],
  };
}

function makeEnv({ allowed = true, response = "Una campana vibra sotto il pelo scuro dell'acqua. Il suono si propaga tra i moli." } = {}) {
  const calls = { ai: [], rateLimit: [] };
  return {
    calls,
    env: {
      NARRATOR_ACCESS_TOKEN: TOKEN,
      NARRATOR_LIMITER: {
        async limit(input) {
          calls.rateLimit.push(input);
          return { success: allowed };
        },
      },
      AI: {
        async run(model, options) {
          calls.ai.push({ model, options });
          return { response };
        },
      },
    },
  };
}

function request(body, { method = "POST", token = TOKEN, headers = {} } = {}) {
  return new Request("https://narrator.test/narrate", {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "CF-Connecting-IP": "203.0.113.8",
      ...headers,
    },
    body: method === "GET" || method === "HEAD" ? undefined : body,
  });
}

test("health endpoint is available without credentials", async () => {
  const response = await worker.fetch(new Request("https://narrator.test/"), {});
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    service: "Dungeon & Bard narrator",
    status: "ok",
  });
});

test("rejects requests without the configured bearer token", async () => {
  const { env, calls } = makeEnv();
  const response = await worker.fetch(request(JSON.stringify(openingRequest()), { token: "wrong" }), env);
  assert.equal(response.status, 401);
  assert.equal(calls.ai.length, 0);
});

test("valid opening request calls Workers AI and returns narration", async () => {
  const { env, calls } = makeEnv();
  const response = await worker.fetch(request(JSON.stringify(openingRequest())), env);
  assert.equal(response.status, 200);
  assert.match((await response.json()).narration, /campana/i);
  assert.equal(calls.ai[0].model, "@cf/meta/llama-3.3-70b-instruct-fp8-fast");
  assert.equal(calls.rateLimit[0].key, "203.0.113.8");
  const prompt = calls.ai[0].options.messages[0].content;
  assert.match(prompt, /never invent or change game rules/i);
  assert.match(prompt, /two brief examples of possible approaches/i);
  assert.match(prompt, /end with one open question/i);
  assert.match(prompt, /Never assign an objective/i);
  assert.match(prompt, /never force a fixed number of scenes/i);
  const context = JSON.parse(calls.ai[0].options.messages[1].content);
  assert.equal(context.party[0].story_ability, "Ispirazione — Usa parole e musica per coinvolgere gli altri.");
});

test("uses supplied class features as narrative strengths without granting automatic bonuses", async () => {
  const { env, calls } = makeEnv();
  await worker.fetch(request(JSON.stringify(openingRequest())), env);
  const prompt = calls.ai[0].options.messages[0].content;
  assert.match(prompt, /story abilities and proficiencies explicitly supplied/i);
  assert.match(prompt, /meaningful way to participate/i);
});

test("keeps check narration vivid without exposing dice mechanics or changing outcomes", async () => {
  const { env, calls } = makeEnv();
  const response = await worker.fetch(request(JSON.stringify(checkRequest(false))), env);
  assert.equal(response.status, 200);
  const prompt = calls.ai[0].options.messages[0].content;
  assert.match(prompt, /supplied d20 result is authoritative/i);
  assert.match(prompt, /useful partial observation when plausible/i);
  assert.match(prompt, /describe concrete sensory details or clues/i);
  assert.match(prompt, /Never answer only that the character failed/i);
  assert.match(prompt, /do not parrot the action/i);
  assert.match(prompt, /mandatory next objective/i);
  assert.match(prompt, /mention numerical dice mechanics/i);
  assert.match(prompt, /end with one natural, open-ended question/i);
});

test("keeps a failed check and its consequence authoritative", async () => {
  const { env, calls } = makeEnv();
  const response = await worker.fetch(request(JSON.stringify(checkRequest(false))), env);
  assert.equal(response.status, 200);
  const context = JSON.parse(calls.ai[0].options.messages[1].content);
  assert.equal(context.official_check_result.passed, false);
  assert.equal(context.official_check_result.total, 7);
  assert.equal(context.current_objective, undefined);
  assert.match(calls.ai[0].options.messages[0].content, /On failure, honor the failure/i);
});

test("narrates actions that need no roll without imposing an objective", async () => {
  const { env, calls } = makeEnv();
  const response = await worker.fetch(
    request(JSON.stringify({
      kind: "freeform",
      language: "it",
      setting: "Un porto in cui le campane suonano sott'acqua.",
      party: [{ name: "Mira", species: "Elfa", class: "Barda" }],
      history: [{ role: "player", content: "Mira accende una lanterna." }],
      action: "Mira accende una lanterna.",
      resolution: "automatic",
      reason: "Accendere una lanterna non richiede una prova.",
    })),
    env,
  );
  assert.equal(response.status, 200);
  const prompt = calls.ai[0].options.messages[0].content;
  assert.match(prompt, /resolved without a die roll/i);
  assert.match(prompt, /Do not create a new mandatory objective/i);
  assert.match(prompt, /end with one natural, open-ended question/i);
});

test("adjudicates a freeform action with a validated local d20 check", async () => {
  const ruling = {
    verdict: "check",
    actor: "Mira",
    ability: "charisma",
    skill: "persuasion",
    dc: 13,
    damage_die: null,
    reason: "Il traghettatore potrebbe non fidarsi.",
  };
  const { env, calls } = makeEnv({ response: JSON.stringify(ruling) });
  const response = await worker.fetch(request(JSON.stringify(adjudicateRequest())), env);
  assert.equal(response.status, 200);
  assert.deepEqual((await response.json()).adjudication, ruling);
  const context = JSON.parse(calls.ai[0].options.messages[1].content);
  assert.equal(context.player_action, "Mira convince il traghettatore a lasciarci passare.");
  assert.equal(context.party[0].abilities.charisma, 15);
  assert.match(calls.ai[0].options.messages[0].content, /Return exactly one JSON object/i);
});

test("allows the narrator to mark routine actions as automatic without a check", async () => {
  const ruling = {
    verdict: "automatic",
    actor: "Mira",
    reason: "La lanterna si accende senza difficoltà.",
  };
  const { env } = makeEnv({ response: JSON.stringify(ruling) });
  const response = await worker.fetch(request(JSON.stringify(adjudicateRequest({
    action: "Mira accende la lanterna.",
  }))), env);
  assert.equal(response.status, 200);
  assert.deepEqual((await response.json()).adjudication, ruling);
});

test("rejects adjudications that invent a character", async () => {
  const { env, calls } = makeEnv({
    response: JSON.stringify({
      verdict: "check",
      actor: "Un personaggio inventato",
      ability: "charisma",
      skill: "persuasion",
      dc: 13,
      damage_die: 6,
      reason: "La prova è difficile.",
    }),
  });
  const response = await worker.fetch(request(JSON.stringify(adjudicateRequest())), env);
  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), { error: "Narrator returned an invalid character." });
  assert.equal(calls.ai.length, 1);
});

test("accepts supported damage dice while keeping the ability check on d20", async () => {
  const { env, calls } = makeEnv();
  const response = await worker.fetch(
    request(JSON.stringify(checkRequest(true, {
      damage_roll: { die: 8, result: 5 },
    }))),
    env,
  );
  assert.equal(response.status, 200);
  const context = JSON.parse(calls.ai[0].options.messages[1].content);
  assert.deepEqual(context.official_check_result.damage_roll, { die: 8, result: 5 });
  assert.equal(context.official_check_result.roll, 3);

  const invalid = await worker.fetch(
    request(JSON.stringify(checkRequest(true, {
      damage_roll: { die: 5, result: 3 },
    }))),
    env,
  );
  assert.equal(invalid.status, 400);
});

test("rejects malformed, oversized, and invalid requests before inference", async () => {
  const { env, calls } = makeEnv();
  const malformed = await worker.fetch(request("{"), env);
  const oversized = await worker.fetch(request("x".repeat(48 * 1024 + 1)), env);
  const invalid = await worker.fetch(request(JSON.stringify(openingRequest({ difficulty: "impossible" }))), env);
  assert.equal(malformed.status, 400);
  assert.equal(oversized.status, 413);
  assert.equal(invalid.status, 400);
  assert.equal(calls.ai.length, 0);
});

test("honors the per-IP rate limiter", async () => {
  const { env, calls } = makeEnv({ allowed: false });
  const response = await worker.fetch(request(JSON.stringify(openingRequest())), env);
  assert.equal(response.status, 429);
  assert.equal(calls.ai.length, 0);
});

test("returns a service error without exposing model errors to the client", async () => {
  const { env } = makeEnv();
  env.AI.run = async () => {
    throw new Error("private provider details");
  };
  const response = await worker.fetch(request(JSON.stringify(openingRequest())), env);
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: "Narrator temporarily unavailable." });
});
