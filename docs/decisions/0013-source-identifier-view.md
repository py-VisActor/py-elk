# 内部identifier文本与原生typed ID

原Node importer以`optString(id)`存储ElkGraph的identifier；JSON数值经`stringVal`转换成Number文本。Spore FIXED preferredRoot比较这个字符串，不能拿原生整数ID直接与首选字符串比较。

`Session.identifier_text(element)`提供该内部视图：字符串原样，整数使用已有`diagnostics.number_text`的Number文本表示；超出binary64的原生大整数在该视图投影为正/负Infinity。该方法接收本session的语义元素，标签缺省ID返回None，不自行生成ID。

原生typed ID、端点索引和输出raw ID继续遵循ADR0002。整数7与字符串"7"仍是两个不同身份；其内部identifier视图可以同为"7"。大整数也不被替换、截断或加范围限制。调用方按实际源的identifier比较/遇到匹配项更新规则使用这个文本，不把它反写为原生身份。

本决定只处理内部identifier文本，不扩展为所有业务字段的数值规范化，不更改已保存JSON输出和先前执行记录。Source Number表示和原生typed身份分别校验，不能用文本相同推导两个原生元素身份相同。
