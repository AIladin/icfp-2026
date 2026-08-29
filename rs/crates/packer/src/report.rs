use std::path::{Path, PathBuf};

use crate::PackError;
use crate::anneal::Candidate;
use crate::design::Design;
use crate::validate::Judged;

pub struct Options<'a> {
    pub design_path: &'a Path,
    pub json: bool,
    pub seed_dim: i32,
    pub seed_judged: Option<&'a Judged>,
}

pub fn write(
    options: &Options<'_>,
    design: &Design,
    results: &[Candidate],
    out: &Path,
) -> Result<(), PackError> {
    let mut payload = Vec::new();
    for (rank, candidate) in results.iter().enumerate() {
        let path = numbered(out, rank);
        std::fs::write(&path, &candidate.source)
            .map_err(|e| PackError(format!("cannot write {}: {e}", path.display())))?;
        let ticks = candidate.judged.as_ref().map(|j| j.avg_ticks);
        let seed_ticks = options.seed_judged.map(|j| j.avg_ticks);
        if options.json {
            payload.push(serde_json::json!({
                "rank": rank,
                "path": path.to_string_lossy(),
                "maxDim": candidate.max_dim,
                "footprint": (candidate.max_dim as i64).pow(2),
                "routeCells": candidate.route_cells,
                "avgTicks": ticks,
            }));
            continue;
        }
        let verdict = match &candidate.judged {
            Some(j) => format!("{}/{} pass, avg {:.1} ticks", j.passed, j.total, j.avg_ticks),
            None => "NOT JUDGED".to_string(),
        };
        let drift = match (ticks, seed_ticks) {
            (Some(now), Some(then)) if then > 0.0 => {
                format!(" ({:+.1}% ticks vs seed)", (now - then) / then * 100.0)
            }
            _ => String::new(),
        };
        println!(
            "#{rank}  max-dim {} (seed {})  footprint {}  pipes {} cells  {verdict}{drift}  -> {}",
            candidate.max_dim,
            options.seed_dim,
            (candidate.max_dim as i64).pow(2),
            candidate.route_cells,
            path.display()
        );
        if rank == 0 {
            for line in &candidate.warnings {
                println!("  {line}");
            }
            for line in &candidate.report {
                println!("  {line}");
            }
        }
    }
    if options.json {
        let text = serde_json::json!({
            "design": options.design_path.to_string_lossy(),
            "problem": design.problem,
            "seedMaxDim": options.seed_dim,
            "candidates": payload,
        });
        println!("{}", serde_json::to_string_pretty(&text).expect("serialisable"));
    }
    println!(
        "\nREMINDER: this is a locally-green CANDIDATE. Submit-test it — the server has loaded a \
         different pipe graph than both local runners before (`icfp submit --wait`)."
    );
    Ok(())
}

pub fn default_out(design: &Path) -> PathBuf {
    let name = design.file_name().unwrap_or_default().to_string_lossy();
    let stem = name.strip_suffix(".eman.toml").unwrap_or(&name);
    design.with_file_name(format!("{stem}.man"))
}

/// `foo.man`, `foo-2.man`, `foo-3.man`, ...
fn numbered(out: &Path, rank: usize) -> PathBuf {
    if rank == 0 {
        return out.to_path_buf();
    }
    let stem = out.file_stem().unwrap_or_default().to_string_lossy();
    let extension = out.extension().unwrap_or_default().to_string_lossy();
    out.with_file_name(format!("{stem}-{}.{extension}", rank + 1))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn design_name_becomes_program_name() {
        assert_eq!(
            default_out(Path::new("programs/demo/v2.eman.toml")),
            Path::new("programs/demo/v2.man")
        );
    }

    #[test]
    fn kept_candidates_are_numbered_after_the_winner() {
        let out = Path::new("programs/demo/v2.man");
        assert_eq!(numbered(out, 0), out);
        assert_eq!(numbered(out, 1), Path::new("programs/demo/v2-2.man"));
        assert_eq!(numbered(out, 2), Path::new("programs/demo/v2-3.man"));
    }
}
