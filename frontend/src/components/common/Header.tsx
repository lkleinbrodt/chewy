import { CalendarIcon, CheckSquare, Settings } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu";

// TODO: Fix issue where the active tab selection is lost on page refresh
// Currently, the index route should show Tasks as selected but this doesn't persist on refresh

const Header = () => {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 mb-1">
      <div className="container flex h-14 items-center">
        <div className="mr-4 flex items-center gap-2">
          <Link to="/" className="flex items-center">
            <img src="/icons/chewy.png" alt="logo" className="w-8 h-8" />
            <span className="ml-2 text-xl text-primary">Chewy</span>
          </Link>
        </div>

        <NavigationMenu className="ml-auto">
          <NavigationMenuList className="gap-2">
            <NavigationMenuItem>
              <NavigationMenuLink
                asChild
                className={
                  navigationMenuTriggerStyle() +
                  " text-sm px-4 py-2 font-medium"
                }
              >
                <NavLink
                  to="/tasks"
                  className={({ isActive }) =>
                    `flex items-center ${
                      isActive ? "bg-accent text-accent-foreground" : ""
                    }`
                  }
                >
                  <CheckSquare className="w-4 h-4 mr-2" />
                  Tasks
                </NavLink>
              </NavigationMenuLink>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink
                asChild
                className={
                  navigationMenuTriggerStyle() +
                  " text-sm px-4 py-2 font-medium"
                }
              >
                <NavLink
                  to="/calendar"
                  className={({ isActive }) =>
                    `flex items-center ${
                      isActive ? "bg-accent text-accent-foreground" : ""
                    }`
                  }
                >
                  <CalendarIcon className="w-4 h-4 mr-2" />
                  Calendar
                </NavLink>
              </NavigationMenuLink>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink
                asChild
                className={
                  navigationMenuTriggerStyle() +
                  " text-sm px-4 py-2 font-medium"
                }
              >
                <NavLink
                  to="/settings"
                  className={({ isActive }) =>
                    `flex items-center ${
                      isActive ? "bg-accent text-accent-foreground" : ""
                    }`
                  }
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Settings
                </NavLink>
              </NavigationMenuLink>
            </NavigationMenuItem>
          </NavigationMenuList>
        </NavigationMenu>
      </div>
    </header>
  );
};

export default Header;
