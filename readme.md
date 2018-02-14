# goomba
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FBattleroid%2Fgoomba.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2FBattleroid%2Fgoomba?ref=badge_shield)


It makes the little ⚠️ (warning) triangles go away in Kibana.

## Usage

See the sample [config][] for a basic setup. Basically just put in pairs of Elasticsearch clusters with their Corresponding Kibana front. Of course, anything set in the defaults will be populated downstream, with the downstream keys taking precedence.

As a CLI you can run `$ goomba config.yaml` or `$ goomba --debug config.yaml` to get more detailed info.

## Notes

* If the config for a cluster is bad (can't connect, bad auth, etc), it'll skip it. Just be aware.
* If you fill only the Elasticsearch URL, but not the Kibana URL it'll use the Elasticsearch URL as the Kibana URL.

[config]: sample.yaml


## License
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FBattleroid%2Fgoomba.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2FBattleroid%2Fgoomba?ref=badge_large)