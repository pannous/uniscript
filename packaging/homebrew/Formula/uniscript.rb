# Homebrew formula for the tap pannous/homebrew-tap (brew install pannous/tap/uniscript): the Rust command line
# `uniscript`, built from the crates.io crate. At a release: sha256 of the published crate
# (curl -sL https://static.crates.io/crates/uniscript/uniscript-VERSION.crate | shasum -a 256), see notes/c-packaging.md
class Uniscript < Formula
  desc "ASCII names for Unicode text (<:alpha> → α, <:fracture A> → 𝔄) and back"
  homepage "https://pannous.com/uniscript/"
  url "https://static.crates.io/crates/uniscript/uniscript-0.2.0.crate"
  sha256 "REPLACE_WITH_SHA256_OF_THE_PUBLISHED_CRATE"
  license "MIT"
  head "https://github.com/pannous/uniscript.git", branch: "main"

  depends_on "rust" => :build

  def install
    system "cargo", "install", *std_cargo_args
  end

  test do
    assert_equal "α 𝔄", shell_output("#{bin}/uniscript '<:alpha> <:fracture A>'").strip
    assert_equal "<:alpha> <:fracture A>", shell_output("#{bin}/uniscript -r 'α 𝔄'").strip
  end
end
