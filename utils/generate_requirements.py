import importlib.metadata

def generate_requirements():
    # Get all installed distributions
    dists = importlib.metadata.distributions()

    # Collect them in a list
    requirements = []
    for dist in dists:
        name = dist.metadata["Name"]
        version = dist.version
        if name and version:
            # Format strictly as requested: Name>=Version
            requirements.append(f"{name}>={version}")

    # Sort alphabetically for a clean list
    requirements.sort()

    # Print to console so you can copy-paste
    print("\n".join(requirements))

if __name__ == "__main__":
    generate_requirements()