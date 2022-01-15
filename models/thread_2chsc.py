import re
from datetime import datetime
import torch
import locale
locale.setlocale(locale.LC_ALL, 'ja_JP.UTF-8')

HARD = 0
SOFT = 1


class Thread(object):
    def __init__(self, title_sp, names, texts, soft_target_range=50, soft_min_score_th=0.6):
        self.title = title_sp.text.strip()
        self.__hard_topics = []
        self.__soft_topics = []
        self.soft_bans = []
        self.hard_bans = []

        self.soft_target_range = soft_target_range
        self.soft_min_score_th = soft_min_score_th

        idx_rep = re.compile('^(\d+)')
        time_rep = re.compile('^：(.+)$')
        sec_rep = re.compile('^\.(\d+)$')
        id_rep = re.compile('^ID:(.+)$')
        one_line = re.compile(
            '^(\d+) ：(.*)：(.+)\.(\d+) (.*\.net).*$')
        pid_rep = re.compile('(&gt;&gt;|>>|＞＞)(\d[\d,]*)')
        remove_rep = re.compile('(http://.*|https://.*|>>\d[\d,]*)')

        self.line = []
        for line_num, (n, t) in enumerate(zip(names, texts)):
            if line_num < 1000:
                self.line.append(
                    Line(n, t, idx_rep, time_rep, sec_rep, id_rep, one_line, pid_rep, remove_rep))

    def hard_topics(self, force=False, sort_by_r=False):
        if self.__hard_topics and not force:
            return self.__hard_topics

        child_list = []
        for l in self.line:
            if l.k_class in self.hard_bans:
                continue
            if not l.parent:
                self.__hard_topics.append([l])
            else:
                for lp in l.parent:
                    if lp['type'] == SOFT:
                        self.__hard_topics.append([l])
                    elif lp['type'] == HARD:
                        child_list.append(l)
                    break

        for cl in child_list:
            ht_flg_list = []
            for p in cl.parent:
                cl_flg = False
                if p['type'] == HARD:
                    for ht_idx, ht in enumerate(self.__hard_topics):
                        if ht_idx not in ht_flg_list:
                            for l in ht:
                                if l.idx == p['idx']:
                                    ht.append(cl)
                                    cl_flg = True
                                    ht_flg_list.append(ht_idx)
                                    break
                            if cl_flg:
                                break

        if sort_by_r:
            self.__hard_topics = [self.sort_by_redirect(
                t) for t in self.__hard_topics]
        return self.__hard_topics

    def soft_topics(self, force=False, sort_by_r=False):
        if self.__soft_topics and not force:
            return self.__soft_topics

        child_list = []
        for l in self.line:
            if l.k_class in self.hard_bans:
                continue
            if not l.parent:
                self.__soft_topics.append([l])
            else:
                for lp in l.parent:
                    if lp['type'] == SOFT:
                        child_list.append(l)
                    elif lp['type'] == HARD:
                        child_list.append(l)
                    break

        for cl in child_list:
            st_flg_list = []
            for p in cl.parent:
                cl_flg = False
                if p['type'] == HARD or p['type'] == SOFT:
                    for st_idx, st in enumerate(self.__soft_topics):
                        if st_idx not in st_flg_list:
                            for l in st:
                                if l.idx == p['idx']:
                                    st.append(cl)
                                    cl_flg = True
                                    st_flg_list.append(st_idx)
                                    break
                            if cl_flg:
                                break
        if sort_by_r:
            self.__soft_topics = [self.sort_by_redirect(
                t) for t in self.__soft_topics]
        return self.__soft_topics

    def vectorize(self, rizer):
        for l in self.line:
            l.vectorize(rizer)

    def set_soft_parent(self, ng_word_ctrl=None):
        for idx, l in enumerate(self.line):
            if idx == 0:
                continue
            if not l.has_parent():
                start_idx = idx - self.soft_target_range
                start_idx = 0 if start_idx < 0 else start_idx
                l.set_soft_parent(self.list_up_soft_target(
                    start_idx, idx, ng_word_ctrl), min_th=self.soft_min_score_th)

    def list_up_soft_target(self, start=0, end=None, ng_word_ctrl=None):
        if end is None:
            end = len(self.line)
        if ng_word_ctrl is None:
            return [l for l in self.line[start:end] if l not in self.soft_bans]
        else:
            return [l for l in self.line[start:end] if l not in self.soft_bans and not ng_word_ctrl.has_ng_word(l.beautified_text())]

    def list_up_hard_target(self, start=0, end=None):
        if end is None:
            end = len(self.line)
        return [l for l in self.line[start:end] if l not in self.hard_bans]

    def get_vectors(self, use_numpy=False):
        vs = []
        for l in self.line:
            vs.append(l.vector)
        vts = torch.stack(vs).squeeze()
        if use_numpy:
            return vts.cpu().numpy()
        else:
            return vts

    def set_k_class(self, model):
        vts_array = self.get_vectors(use_numpy=True)
        k_cls_results = model.predict(vts_array)
        for l, k_cls in zip(self.line, k_cls_results):
            l.k_class = k_cls

    def set_ban_k_class(self, soft_bans, hard_bans):
        self.soft_bans = soft_bans
        self.hard_bans = hard_bans

    def sort_by_redirect(self, topic):
        if len(topic) == 1:
            return topic

        new_list = []
        child_list = []
        nchild_list = []
        parent_idx = topic[0].idx
        for l in topic[1:]:
            l_flg = False
            for lp in l.parent:
                if lp['idx'] == parent_idx:
                    child_list.append(l)
                    l_flg = True
                    break
            if not l_flg:
                nchild_list.append(l)

        new_list.extend(child_list)
        new_list.extend(nchild_list)
        sorted_list = [topic[0]]
        sorted_list.extend(self.sort_by_redirect(new_list))

        return sorted_list


class Line(object):
    def __init__(self, name_sp, text_sp, idx_rep, time_rep, sec_rep, id_rep, one_line, pid_rep, remove_rep):
        self.pid_rep = pid_rep
        self.remove_rep = remove_rep
        self.vector = None
        self.k_class = None
        self.set_param(name_sp, text_sp, idx_rep,
                       time_rep, sec_rep, id_rep, one_line)
        self.set_parent()

    def set_param(self, name_sp, text_sp, idx_rep, time_rep, sec_rep, id_rep, one_line):
        self.name = name_sp.select_one('b').text.strip()
        self.text = text_sp.text.strip()
        self.edit_text()
        names = name_sp.text.splitlines()

        if len(names) == 1:
            results = one_line.match(names[0].strip())
            self.idx = int(results.group(1))
            self.time = results.group(3)
            sec = results.group(4)
            self.id = results.group(5)
        else:
            new_names = [n for n in names if n != '']
            self.idx = int(idx_rep.match(new_names[0].strip()).group(1))
            for n in names[3:-2]:
                result = time_rep.match(n.strip())
                if result:
                    self.time = result.group(1)
                    break
            for n in names[3:-2]:
                result = sec_rep.match(n.strip())
                if result:
                    sec = result.group(1)
                    break
            id_result = id_rep.match(names[-2].strip())
            self.id = '.net' if id_result is None else id_result.group(1)
        fdt = self.time.split('(')[0].strip()
        sdt = self.time.split(')')[1].strip()
        self.time = datetime.strptime(
            f'{fdt} {sdt}.{sec}', '%Y/%m/%d %H:%M:%S.%f')

    def edit_text(self):
        new_texts = []
        if len(self.text.splitlines()) == 1:
            sep = '  '
        else:
            sep = '\n'
        for l in self.text.split(sep):
            if '(deleted an unsolicited ad)' in l:
                l = l.replace('(deleted an unsolicited ad)', '')
            if l.strip() != '':
                new_texts.append(l.strip())
        self.text = '\n'.join(new_texts)

    def set_parent(self):
        self.parent = []
        p_list = self.extract_parent()
        if p_list:
            p_list = [{'idx': p, 'type': HARD} for p in p_list]
            self.parent.extend(p_list)

    def extract_parent(self):
        text_lines = self.text.splitlines()
        p_list = []
        for l in text_lines:
            results = self.pid_rep.findall(l.strip())
            if results:
                for r in results:
                    r_num = []
                    if ',' in r[1]:
                        r_num.extend([int(n) for n in r[1].split(',')])
                    else:
                        r_num.append(int(r[1]))
                    for rn in r_num:
                        if rn != self.idx and rn < self.idx:
                            p_list.append(rn)
                p_list.extend(results)
        p_set = set(p_list)
        return list(p_set)

    def add_soft_parent(self, idx, score):
        sp = {'idx': idx, 'type': SOFT, 'score': score}
        self.parent.append(sp)

    def joined_text(self, keyword=' '):
        return keyword.join(self.text.splitlines())

    def beautified_text(self, keyword='\n'):
        lines = self.text.splitlines()
        new_texts = []
        for l in lines:
            new_l = ''

            new_l = self.remove_rep.sub('', l.strip())

            if new_l != '':
                new_texts.append(new_l)
        if not new_texts:
            new_texts.append('')
        return keyword.join(new_texts)

    def has_parent(self, type=None):
        if not self.parent:
            return False
        else:
            if type is None:
                return True
            else:
                for p in self.parent:
                    if p['type'] == type:
                        return True
                return False

    def set_soft_parent(self, other_lines, min_th=0.5):
        from sentence_transformers import util
        import torch
        other_embeddings = [l.vector for l in other_lines]
        other_embeddings = torch.vstack(other_embeddings)
        cosine_scores = util.pytorch_cos_sim(self.vector, other_embeddings)
        reductions = torch.linspace(
            0.0, 1.0, len(other_lines)).to(cosine_scores.device)
        other_line_idx = torch.argmax(cosine_scores[0]*reductions)
        # other_line_idx = torch.argmax(cosine_scores[0])
        # if min_th < cosine_scores[0][other_line_idx]*reductions[other_line_idx]:
        if min_th < cosine_scores[0][other_line_idx]:
            self.add_soft_parent(
                other_lines[other_line_idx.item()].idx,
                cosine_scores[0][other_line_idx].item()
            )

    def vectorize(self, rizer):
        self.vector = rizer.vectorize([self.beautified_text('\n')])
        return self.vector

    def get_text_as_title(self, lenght_th=10):
        text = self.beautified_text('\n')
        texts = text.splitlines()
        if len(texts) == 1:
            return texts[0]
        else:
            if len(texts[0]) <= lenght_th:
                return f'{texts[0]} {texts[1]}'
            else:
                return texts[0]


class Thread_list(object):
    def __init__(self, title_sp, thlist_sp):
        self.title = title_sp.text.strip()

        data_rep = re.compile('^\d+: (.+) \((\d+)\)$')

        self.datas = []
        for sp in thlist_sp:
            result = data_rep.match(sp.text.strip())
            url_id = sp['href'].split('/')[0]
            item = {
                'url_id': url_id,
                'line_num': int(result.group(2).strip()),
                'title': result.group(1).strip(),
            }
            self.datas.append(item)
