#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import baker
from commands import getoutput
import time
import os
from os.path import join as opj

import pandas as pd
import matplotlib.pyplot as plt

# TODO: find an heuristic to fetch samples from sitemap.xml
URLS = '''
/blog/our-blog-1/post/the-future-of-emails-1
/forum/help-1
/forum/help-1/question/how-to-configure-alerts-for-employee-contract-expiration-1
/jobs
/jobs/detail/marketing-and-community-manager-6
/shop
/slides/partner-channel-2
/website/info
/page/website.aboutus
/customers
'''.strip().split()

BASE_URL = 'http://127.0.0.1:8069'

AB_SUMMARY = ('Time per request:', 'Document Path:', 'Requests per second:', 'Failed requests:')


@baker.command
def ab(concurrency=10, requests=1000, confirm=False, pause=0, dir='output'):
    """Apache benchmark"""
    try:
        os.makedirs(dir)
    except OSError:
        pass

    for path in URLS:
        url = BASE_URL + path
        basename = path.replace('/', '-').strip('-')
        tsv_file = opj(dir, basename + '.tsv')
        cmd = 'ab -c %s -g %s.tsv -n %s %s' % (concurrency, tsv_file, requests, url)
        if confirm and not raw_input("Benchmarking %s." % url).strip():
            continue
        print("Starting benchmark for %s" % url)
        code = getoutput('curl -s -o /dev/null -w "%%{http_code}" %s' % url)  # warmup
        assert int(code) == 200, "Route %s returned %s http code" % (url, code)

        out = getoutput(cmd)
        with open(opj(dir, basename + '.log'), 'w') as f:
            f.write(out)
        doc = ['-' * 80]
        for line in out.splitlines():
            if line.startswith(AB_SUMMARY):
                doc.append(line)
        with open(opj(dir, 'summary.log'), 'a') as f:
            output = '\n'.join(doc) + '\n'
            print(output)
            f.write(output)
        if not confirm and pause:
            print("Pause for %s seconds..." % pause)
            time.sleep(pause)


@baker.command
def plot(branches, output=None, dpi=300):
    """Draw benchmark plot"""
    branches = branches.split(',')
    raw_data = {}
    colors = ['#EE3224', '#F78F1E', '#FFC222', '#EEEF55']  # TODO: generate rainbow
    pages = "Blog post,Forum,Forum post,Jobs,Job post,Shop,Slide,Info,About us,Customers".split(',')
    raw_data['pages'] = pages
    for branch in branches:
        nums = []
        with open('%s/summary.log' % branch, 'r') as f:
            for line in f.readlines():
                if line.startswith('Requests per second:'):
                    num = float(line.split(':')[1].split('[')[0].strip())
                    nums.append(num)
            raw_data[branch] = nums
    df = pd.DataFrame(raw_data, columns=['pages'] + branches)

    pos = list(range(len(df[branches[0]])))
    width = 1 / (len(branches) + 1)

    fig, ax = plt.subplots(figsize=(15, 5))

    ymax = 0
    for i, branch in enumerate(branches):
        ymax = max(ymax, *df[branch])
        plt.bar([p + width * i for p in pos],
                df[branch],
                width,
                alpha=0.5,
                color=colors[i],
                label=branches[i])

    ax.set_ylabel('Req/sec')
    ax.set_title('Website pages')
    ax.set_xticks([p + 1.5 * width for p in pos])
    ax.set_xticklabels(df['pages'])

    plt.xlim(min(pos) - width, max(pos) + width * 4)
    plt.ylim([0, ymax * 1.2])

    plt.legend(branches, loc='upper left')
    plt.grid(axis='y', color='#999999')
    if output is None:
        plt.show()
    else:
        plt.savefig(output, dpi=dpi)


if __name__ == '__main__':
    baker.run()
