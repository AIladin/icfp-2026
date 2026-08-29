//! Test cases as the contest API ships them.
//!
//! Mirrors `icfp_api.models.TestCase` / `Round`, including the one normalisation that matters:
//!
//! > Most problems return `{"name", "rounds": [...]}`; some (e.g. `triangle`) return a flat
//! > `{"name", "in", "out"}` with no `rounds` key at all.
//! > — `docs/vault/heap/publicTestData has two shapes.md`
//!
//! Values arrive as strings on the wire and are parsed to `i64` by the judge, the same as the
//! Python runner's `int(value)`.

use serde::Deserialize;
use serde_json::Value;

/// One input/expected-output pair. All rounds of a case run against a single program run.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct Round {
    #[serde(rename = "in", default)]
    pub inputs: Vec<String>,
    #[serde(default)]
    pub out: Vec<String>,
    /// Display-judged problems (e.g. `palette`) are compared frame by frame instead of on output.
    #[serde(default)]
    pub frames: Option<Vec<Vec<String>>>,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct RawCase {
    #[serde(default)]
    name: String,
    /// Absent — not merely empty — is what selects the flat shape, exactly as the Python
    /// `model_validator` tests `"rounds" in data`.
    rounds: Option<Vec<Round>>,
    #[serde(rename = "in", default)]
    inputs: Vec<String>,
    #[serde(default)]
    out: Vec<String>,
    #[serde(default)]
    frames: Option<Vec<Vec<String>>>,
}

#[derive(Debug, Clone, Default)]
pub struct TestCase {
    pub name: String,
    pub rounds: Vec<Round>,
}

impl From<RawCase> for TestCase {
    fn from(raw: RawCase) -> Self {
        let RawCase { name, rounds, inputs, out, frames } = raw;
        match rounds {
            Some(rounds) => Self { name, rounds },
            None => Self { name, rounds: vec![Round { inputs, out, frames }] },
        }
    }
}

impl TestCase {
    pub fn from_json(value: Value) -> serde_json::Result<Self> {
        Ok(serde_json::from_value::<RawCase>(value)?.into())
    }
}

/// A problem as `icfp problem <slug> --json` prints it. Only the fields a run needs.
#[derive(Debug, Clone, Default, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Problem {
    #[serde(default)]
    pub slug: String,
    #[serde(default)]
    pub scoring: String,
    #[serde(default)]
    pub tick_cap: Option<u64>,
    #[serde(default)]
    public_test_data: Vec<RawCase>,
}

impl Problem {
    pub fn cases(&self) -> Vec<TestCase> {
        self.public_test_data.iter().cloned().map(TestCase::from).collect()
    }
}

/// Read cases from either shape `--cases` accepts: the bare list `icfp tests` writes, or a whole
/// problem object with a `publicTestData` key.
pub fn parse_cases(payload: &str) -> serde_json::Result<Vec<TestCase>> {
    let value: Value = serde_json::from_str(payload)?;
    let items = match value {
        Value::Object(map) => {
            map.get("publicTestData").cloned().unwrap_or_else(|| Value::Array(Vec::new()))
        }
        other => other,
    };
    let raw: Vec<RawCase> = serde_json::from_value(items)?;
    Ok(raw.into_iter().map(TestCase::from).collect())
}
