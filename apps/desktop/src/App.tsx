import { DesktopWorkspace } from "./features/workspace/DesktopWorkspace";
import { I18nProvider } from "./lib/i18n";

export function App() {
  return (
    <I18nProvider>
      <DesktopWorkspace />
    </I18nProvider>
  );
}
