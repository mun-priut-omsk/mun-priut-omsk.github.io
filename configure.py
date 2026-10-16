import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--owner',required=True);p.add_argument('--repo',default='dogs');p.add_argument('--auth-site',default='');args=p.parse_args()
assert re.fullmatch(r'[A-Za-z0-9-]+',args.owner) and re.fullmatch(r'[A-Za-z0-9_.-]+',args.repo)
root=Path(__file__).resolve().parent;path=root/'settings.json';settings=json.loads(path.read_text(encoding='utf-8'))
site_url=f'https://{args.owner}.github.io/' if args.repo.lower()==f'{args.owner}.github.io'.lower() else f'https://{args.owner}.github.io/{args.repo}/'
settings.update(github_owner=args.owner,github_repo=args.repo,site_url=site_url,auth_site=args.auth_site)
path.write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8');print('Site settings saved; no passwords or secrets required.')
