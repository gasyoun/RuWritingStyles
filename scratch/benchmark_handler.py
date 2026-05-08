def cmd_eval_benchmark(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    models = args.models
    provider = args.provider
    
    print(f"Starting benchmark for {len(models)} models on {provider}...")
    
    suite_paths = []
    
    for model in models:
        print(f"\n>>> Benchmarking Model: {model}")
        suite_id = f"benchmark-{model.replace('.', '-').lower()}"
        
        suite_args = argparse.Namespace(
            suite_id=suite_id,
            execute=True,
            provider=provider,
            model=model,
            require_provider_ready=False,
            strict=False,
            compare_to=None,
            deliberate=True,
            scrutiny=True,
        )
        
        try:
            status = cmd_eval_suite(suite_args)
            if status == 0:
                suite_paths.append(repo_root / "runs" / suite_id / "eval-suite-result.json")
        except Exception as e:
            print(f"error: failed to benchmark {model}: {e}")
            
    if suite_paths:
        from .evals import generate_leaderboard_report
        report_path = generate_leaderboard_report(repo_root, suite_paths)
        print(f"\nBenchmark Complete! Leaderboard report: {report_path.relative_to(repo_root)}")
        return 0
        
    return 1
