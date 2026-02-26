/**
 * instrumentation.js — graph-viz example
 *
 * In a real project this would import layout_metrics from your app and run
 * a headless simulation.  Here we produce synthetic metrics for illustration.
 *
 * Run:   node instrumentation.js <scenario>
 * Output: metrics.json
 */

const fs = require("fs");

const scenario = process.argv[2] || process.env.USERSIM_SCENARIO || "small_single_module";

// Synthetic metrics per scenario — replace with real measurements from your app
const SCENARIOS = {
  small_single_module: {
    node_count: 20, edge_count: 35, module_count: 1, is_blob_mode: false,
    layout_stress: 0.8, edge_crossing_ratio: 0.05, blob_separation: 1.0,
    hub_centrality_error: 0.2, node_size_cv: 0.45, blob_edge_routing: 0.0,
    inter_module_crossings: 0, has_linear_chains: true,
  },
  five_modules_gateway: {
    node_count: 127, edge_count: 340, module_count: 5, is_blob_mode: true,
    layout_stress: 1.2, edge_crossing_ratio: 0.08, blob_separation: 0.72,
    hub_centrality_error: 0.28, node_size_cv: 0.38, blob_edge_routing: 0.18,
    inter_module_crossings: 3, has_linear_chains: true,
  },
  spaghetti_large: {
    node_count: 450, edge_count: 2800, module_count: 12, is_blob_mode: true,
    layout_stress: 3.1, edge_crossing_ratio: 0.68, blob_separation: 0.31,
    hub_centrality_error: 0.71, node_size_cv: 0.12, blob_edge_routing: 0.55,
    inter_module_crossings: 47, has_linear_chains: false,
  },
};

const metrics = SCENARIOS[scenario];
if (!metrics) {
  console.error(`Unknown scenario: ${scenario}`);
  console.error(`Available: ${Object.keys(SCENARIOS).join(", ")}`);
  process.exit(1);
}

const output = {
  schema:   "usersim.metrics.v1",
  scenario,
  metrics,
};

fs.writeFileSync("metrics.json", JSON.stringify(output, null, 2));
console.log(`[instrumentation] scenario=${scenario} nodes=${metrics.node_count}`);
