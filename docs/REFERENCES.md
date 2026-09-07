# 注釈付き文献・一次資料リスト

調査日: **2026-09-05**。番号はこのリポジトリ内で固定。
本文の転載・第三者PDFは同梱しない。確認範囲を区別し、書誌を見ただけの資料を精読済みとはしない。
論文用の引用は `references.bib`、公式ソフトウェア資料は下記URLを使用する。
動的なlatest/masterページは今後更新されるため、実際の導入時にはバージョンとcommitを記録する。

## RFの定義・先行研究

**R1. E. Jensen, “Cavity basics.”** CERN Yellow Report CERN-2011-007, pp.259–275; arXiv:1201.3202 (2012登録)。
[arXiv・書誌](https://arxiv.org/abs/1201.3202)
— 閲覧: 著者・書誌・概要。導波管、共振モード、ビームとの相互作用を学ぶ入口。初期実装の背景文献。

**R2. E. Jensen, “RF Cavity Design.”** CERN-2014-009, pp.405–429 (2014)。DOI: 10.5170/CERN-2014-009.405。
[CERN公開原稿](https://cds.cern.ch/record/1982429/files/405-429%20Jensen.pdf)
— 閲覧: 論文冒頭とRF量の節。R/Qとエネルギーの定義を比較する資料。特に係数2の規約を式から確認する。

**R3. S. Udongwo and U. van Rienen, “An open-source Python tool for the Maxwell eigenvalue problem and multipacting analysis in axisymmetric elliptical cavity structures.”** IPAC2024, MOPS27, pp.771–774 (2024)。DOI: 10.18429/JACoW-IPAC2024-MOPS27。
[JACoW書誌](https://proceedings.jacow.org/ipac2024/doi_per_institute/mops27/index.html) · [公開論文](https://inspirehep.net/files/0a80007ba7602a4038a4802675dc00e5)
— 閲覧: 書誌・概要・Maxwell問題の冒頭。PyMultipact/NGSolveの先行例。今回の粒子追跡実装を意味しない。

**R4. R. Hiptmair and P. D. Ledger, “Computation of Resonant Modes for Axisymmetric Cavities using hp-Version Finite Elements.”** ETH SAM Research Report 2003-15, November 2003。
[著者所属機関の公開原稿](https://www.sam.math.ethz.ch/sam_reports/reports_final/reports2003/2003-15_fp.pdf)
— 閲覧: 要旨、問題設定、軸条件の節。高次・混合空間・角部の特異性の参考。今回のP1スカラー実装そのものの収束定理として引用しない。

**R5. R. Hiptmair, “Finite elements in computational electromagnetism.”** Acta Numerica 11, pp.237–339 (2002)。DOI: 10.1017/S0962492902000041。
[出版社](https://www.cambridge.org/core/journals/acta-numerica/article/abs/finite-elements-in-computational-electromagnetism/C145D69E9F4109563E8EFFB9DB963C09) · [著者公開原稿](https://people.math.ethz.ch/~hiptmair/Courses/CEM/HIP02.pdf)
— 閲覧: 出版社/機関の書誌と概要。今後H(curl)・nullspaceを実装する前の精読対象。

**R6. Dark-Elektron, cavsim2d.**
[開発元リポジトリ](https://github.com/Dark-Elektron/cavsim2d)
— 閲覧: README、機能表、依存関係、ライセンス表示。ソルバ内部は未閲覧、未実行。MITの表示とABCI別実行形式の記述を区別している。

**R7. “Reference manual for the POISSON/SUPERFISH Group of Codes.”** Los Alamos report LA-UR-87-126 (1987)、419ページ。
[DOE資料の保存書誌](https://digital.library.unt.edu/ark:/67531/metadc1317114/) · [OSTI識別子](https://www.osti.gov/biblio/10140827)
— 閲覧: UNTの書誌・概要のみ。OSTI直接アクセスは取得できなかった。マニュアル本文・ソースは取得していない。磁場/RFの歴史的用途の確認用。

## 数値ライブラリと将来の基盤

**R8. SciPy, `scipy.sparse.linalg.eigsh` API.**
[公式API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html)
— 閲覧: 一般化固有値・shift-invert・引数の説明。今回実行したSciPyは1.17.0で、閲覧時のWeb文書表示は1.18.0。使用している基本APIはローカル実行でも確認。

**R9. C. Geuzaine and J.-F. Remacle, Gmsh reference manual.**
[公式マニュアル](https://gmsh.info/doc/texinfo/gmsh.html)
— 閲覧: 機能一覧・形状/メッシュ概要・Copying conditions/Appendix F。表示版4.15.2。導入・実行は未実施。

**R10. C. Geuzaine and J.-F. Remacle, “Gmsh: A 3-D finite element mesh generator with built-in pre- and post-processing facilities.”** International Journal for Numerical Methods in Engineering 79(11), pp.1309–1331 (2009)。DOI: 10.1002/nme.2579。
[出版社](https://onlinelibrary.wiley.com/doi/10.1002/nme.2579) · [著者所属機関の記録](https://orbi.uliege.be/handle/2268/22742)
— 閲覧: 書誌。Gmshを採用した場合の引用元。

**R11. MFEM, Example 13: Maxwell Eigenproblem; LICENSE.**
[公式例一覧](https://mfem.org/examples/?hcurl=) · [ライセンス](https://github.com/mfem/mfem/blob/master/LICENSE)
— 閲覧: 例一覧と公式ライセンス。Example 13のソース本体は未閲覧、未実行。Maxwell固有値例の存在を確認。

**R12. Palace documentation.**
[公式概要](https://awslabs.github.io/palace/stable/) · [問題種別](https://awslabs.github.io/palace/stable/guide/problem/) · [LICENSE](https://github.com/awslabs/palace/blob/main/LICENSE)
— 閲覧: 機能概要・問題種別・ライセンス。3D比較先候補。すべての将来機能が現在利用できるとは仮定しない。

**R13. P. Dular and C. Geuzaine, GetDP official documentation.**
[公式サイト](https://getdp.info/)
— 閲覧: 軸対称を含む対応形式、配布条件、引用先。DSLによる有限要素問題記述。今回利用なし。

**R14. T. Liebig / openEMS project, Introduction.**
[公式文書](https://docs.openems.de/intro.html)
— 閲覧: EC-FDTD、円筒座標、PML、ライセンス、Python等の概要。今回利用なし。

**R15. SLEPc, EPS manual.**
[公式EPS文書](https://slepc.upv.es/release/documentation/manual/eps.html)
— 閲覧: 固有値問題ソルバ概要。表示版3.25.1。MPI/SLEPcバックエンドはロードマップ上の候補で、同梱なし。

**R16. V. Hernandez, J. E. Roman and V. Vidal, “SLEPc: A scalable and flexible toolkit for the solution of eigenvalue problems.”** ACM Transactions on Mathematical Software 31(3), pp.351–362 (2005)。DOI: 10.1145/1089014.1089019。
[公式引用案内](https://slepc.upv.es/release/slepc4py/citing.html)
— 閲覧: 公式の引用書誌。大規模化する場合の基礎文献。

**R17. NGSolve project / LICENSE.**
[公式リポジトリ](https://github.com/NGSolve/ngsolve) · [LICENSE](https://github.com/NGSolve/ngsolve/blob/master/LICENSE)
— 閲覧: 公開概要・ライセンスページ。今回未導入。独立比較バックエンドとして選定する際に、使用バージョンの依存物まで確認する。

## 定数・ライセンス・由来

**R18. Apache Software Foundation, Apache License Version 2.0.**
[公式ライセンス](https://www.apache.org/licenses/LICENSE-2.0.txt)
— 閲覧: 正式な条文。プロジェクトライセンスとして採用。LICENSE全文はローカルOSの標準ライセンスファイルから同梱した。

**R19. NIST, CODATA value: vacuum magnetic permeability.**
[公式定数ページ](https://physics.nist.gov/cgi-bin/cuu/Value?mu0)
— 閲覧: CODATA定数ページ。使用値を `constants.py` に固定。

**R20. NumPy project, LICENSE.txt.**
[開発元ライセンス](https://github.com/numpy/numpy/blob/main/LICENSE.txt)
— 閲覧: BSD 3-Clause条文。配布wheelには別の同梱依存物があり得る。

**R21. SciPy project, LICENSE.txt.**
[開発元ライセンス](https://github.com/scipy/scipy/blob/main/LICENSE.txt)
— 閲覧: 開発元ライセンス。今回のZIPにNumPy/SciPy本体は同梱しない。

## 可視化の検証

**R22. Chrome for Developers, Chrome Headless mode.**
[公式文書](https://developer.chrome.com/docs/automation-and-testing/headless)
— 2026-09-05閲覧。可視ウィンドウを表示しない自動テスト方法を確認。数値ソルバーには利用しない。

**R23. Chrome DevTools Protocol, Target / Runtime / Page / Input domains.**
[公式プロトコル](https://chromedevtools.github.io/devtools-protocol/)
— 2026-09-05閲覧。公開Target/Runtime APIを確認し、実ブラウザーでキー入力・状態・スクリーンショットを検査した。
第三者の通信ライブラリやコードをコピーせず、Node標準WebSocketで呼び出す。

## 角点の診断

**R24. William F. Mitchell, A Collection of 2D Elliptic Problems for Testing Adaptive Algorithms.**
NISTIR 7668 (2010), §2.2 Reentrant Corner。
[NIST公式PDF](https://math.nist.gov/~WMitchell/papers/nistir7668.pdf)
— 2026-09-06閲覧。角度ωに対する局所解のべき指数π/ωを確認。
RFのNeumann主部への対応はSURFACE_FIELD_DIAGNOSTICS.mdで別途導出し、
数値解の補正や解析値による置換には用いない。外部コードのコピーなし。

**R25. Los Alamos Accelerator Code Group, Poisson Superfish v7, SFCODES.DOC.**
— 2026-09-06、ユーザーが許可したローカルインストールの付属公式文書を閲覧。
AutomeshのPO入力欄NT/RADIUSで円弧方向の指定（NT=4/5）を確認した。
文書はローカルの外部参照であり、実装・配布へ同梱しない。ソースコードの参照・転用なし。

## 互換計画の機能調査

**R26. OECD/NEA, ESTS0428/01 POISSON, SUPERFISH program abstract.**
[公式配布機関の機能概要](https://www.oecd-nea.org/tools/abstract/detail/ests0428/)
— 2026-09-07閲覧。登録更新日は2001-05-03。RF/静的場・座標系・幾何・周辺機能の分類に使用。
対象7.xの詳細仕様と同一とはしない。概要には数値法の説明も表示されるが今回の実装へ転用しない。
ソース・実行形式・配布アーカイブのリンクには進んでいない。

**R27. USPAS 2024, PILA lecture 10, p.44.**
[Fermilab/USPAS公開講義](https://uspas.fnal.gov/materials/24RohnertPark/PILA/10.pdf)
— 2026-09-07閲覧。Poisson/Superfishの平面/軸対称RF・静電・静磁場、メッシュ・後処理の概要を確認。
マニュアル本文・旧ソースの代替仕様には使わない。PDFや図は同梱しない。

**R28. NIST Digital Library of Mathematical Functions, §§10.47, 10.51.**
[球ベッセルの定義と微分方程式](https://dlmf.nist.gov/10.47)、
[漸化式・微分](https://dlmf.nist.gov/10.51) — 2026-09-08閲覧。
球形PECの独立参照に特殊関数の定義を使用。空洞のPEC条件・エネルギー/RF積分は独自導出。
本文・画像・コードは転載していない。

## 参照の推奨順序

RFの規約はR1→R2、軸対称の数値解析はR4→R5、既存OSSとの役割比較はR3→R6、
バックエンド選定はR11→R17→R12、メッシュはR9→R10、大規模固有値はR15→R16。
R7は歴史的背景として別扱いにし、実装のcanonical sourceは本リポジトリのPHYSICS.mdとする。
